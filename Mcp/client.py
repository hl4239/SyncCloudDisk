import asyncio
import json
import os
from pathlib import Path
import settings # Assuming your settings.py is accessible

# Ensure imports from mcp and openai are correct
# from mcp import ClientSession, StdioServerParameters, stdio_client # Hypothetical imports
# Need actual imports for stdio_client, ClientSession, StdioServerParameters
# Example using placeholder names if library structure is different:
from mcp import ClientSession, StdioServerParameters, stdio_client # Replace with actual imports!

from openai import OpenAI, AsyncOpenAI # Use AsyncOpenAI for await client.chat...

# --- Configuration ---
# Best practice: Define project_root clearly, maybe outside the class
# or pass it during initialization.
try:
    # Assumes this script is in a subdirectory relative to the project root
    # Adjust the Path traversal ( .parent calls ) as needed
    project_root = Path(__file__).parent.parent
    print(f"Project Root detected: {project_root}")
    # Construct the path to server.py relative to the project root
    server_script_path = project_root / 'Mcp' / 'server.py' # Use Path objects for joining
    if not server_script_path.is_file():
        raise FileNotFoundError(f"Server script not found at: {server_script_path}")
    print(f"Server script path: {server_script_path}")
except NameError:
    print("Warning: Could not determine project_root automatically (maybe running interactively?). Set it manually.")
    # Set manually if needed, e.g.:
    # project_root = Path("/path/to/your/project")
    # server_script_path = project_root / 'Mcp' / 'server.py'
    # Handle the error appropriately if root cannot be determined
    project_root = None # Or raise an error

# --- Reusable Client Class ---

class ReusableChatClient:
    """
    A reusable client that maintains a connection to an MCP server
    and interacts with an OpenAI compatible API.
    """
    def __init__(self):
        self.openai_api_key = settings.Current_AI['key']
        self. openai_base_url = settings.Current_AI['url']
        self. server_script = server_script_path  # Use the determined path
        if not self.server_script or not self.server_script.is_file():
             raise ValueError(f"Invalid server script path provided: {self. server_script}")

        self.server_params = StdioServerParameters(
            command="python", # Consider using sys.executable for portability
            args=[str(self. server_script)], # Convert Path to string for subprocess
            env={**os.environ, "PYTHONUTF8": "1"},
        )
        # Use AsyncOpenAI because ask_question is async and calls create
        self.openai_client = AsyncOpenAI(
            api_key=self.openai_api_key,
            base_url=self.openai_base_url,
        )
        self._stdio_cm = None
        self._session_cm = None
        self.session: ClientSession | None = None # Type hint for clarity
        self.available_tools: list = []
        self._read = None
        self._write = None
        self._is_initialized = False # Track initialization state


    async def __aenter__(self):
        """Initializes the MCP connection when entering the 'async with' block."""
        if self._is_initialized:
            print("Client already initialized.")
            return self

        print('正在初始化 MCP 连接...')
        try:
            self._stdio_cm = stdio_client(self.server_params)
            self._read, self._write = await self._stdio_cm.__aenter__()

            self._session_cm = ClientSession(self._read, self._write)
            self.session = await self._session_cm.__aenter__()

            await self.session.initialize()
            print("MCP 连接已建立")

            await self._fetch_and_process_tools()

            self._is_initialized = True
            print("MCP Client 初始化完成。")

        except Exception as e:
            print(f"初始化 MCP 连接或获取工具时出错: {e}")
            # Attempt cleanup even if initialization failed partially
            await self.__aexit__(type(e), e, e.__traceback__)
            raise # Re-raise the exception after cleanup attempt
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleans up the MCP connection when exiting the 'async with' block."""
        if not self._is_initialized and not self._stdio_cm and not self._session_cm:
            # Avoid closing if initialization never started properly or already closed
            print("MCP Client 未初始化或已关闭。")
            return False # Indicate no exception suppression needed if already clean

        print("正在关闭 MCP 连接...")
        session_exc = None
        stdio_exc = None

        # Close session first
        try:
            if self._session_cm:
                # Pass exception info for proper context manager cleanup
                await self._session_cm.__aexit__(exc_type, exc_val, exc_tb)
        except Exception as e:
            session_exc = e
            print(f"关闭 ClientSession 时出错: {e}")
            # If no original exception, this becomes the primary one
            if not exc_type:
                 exc_type, exc_val, exc_tb = type(e), e, e.__traceback__

        # Close stdio client next
        try:
            if self._stdio_cm:
                 # Pass original or session exception info
                await self._stdio_cm.__aexit__(exc_type, exc_val, exc_tb)
        except Exception as e:
            stdio_exc = e
            print(f"关闭 stdio_client 时出错: {e}")
            # Optionally record this error too, perhaps raise a combined error later

        # Reset state
        self.session = None
        self.available_tools = []
        self._session_cm = None
        self._read = None
        self._write = None
        self._stdio_cm = None
        self._is_initialized = False
        print("MCP 连接已关闭。")

        # If errors occurred during cleanup, decide how to report them.
        # For now, we just print them.
        # Return False to propagate the *original* exception (if any)
        # that caused the __aexit__. If cleanup itself failed without an
        # original exception, those errors were printed but not raised here.
        return False # Propagate original exceptions


    async def _fetch_and_process_tools(self):
        """Fetches tools from the MCP server and formats them for OpenAI."""
        if not self.session:
            print("错误：尝试在没有活动会话的情况下获取工具。")
            return

        print("\n尝试获取 MCP 工具列表...")
        try:
            response = await self.session.list_tools()
            if response and hasattr(response, 'tools'):
                print("\n可用 MCP 工具:")
                print('---------------- MCP Tools ----------------------')
                # Consider printing response selectively if it's very large
                # print(response)
                self.available_tools = []
                for tool in response.tools:
                     # Basic validation of tool structure before accessing keys
                     if not hasattr(tool, 'name') or not hasattr(tool, 'description') or not hasattr(tool, 'inputSchema'):
                         print(f"警告: 跳过格式不正确的工具: {tool}")
                         continue

                     input_schema = tool.inputSchema
                     properties = input_schema.get('properties', {})
                     required = input_schema.get('required', [])

                     # Validate properties structure
                     formatted_properties = {}
                     for key, value in properties.items():
                         if isinstance(value, dict) and 'type' in value:
                             formatted_properties[key] = {
                                 'type': value['type'],
                                 # Use .get() for safer access to optional 'title'
                                 "description": value.get('title', f'Parameter {key}')
                             }
                         else:
                              print(f"警告: 跳过工具 '{tool.name}' 中格式不正确的属性 '{key}': {value}")

                     self.available_tools.append({
                        "type": "function",
                        "function": {
                            "name": tool.name,
                            "description": tool.description,
                            "parameters": {
                                "type": "object", # Standard for OpenAI functions
                                "properties": formatted_properties,
                                "required": required,
                            }
                        }
                    })
                print("\n格式化后的 OpenAI 工具:")
                print(json.dumps(self.available_tools, indent=2))
            else:
                print("未能从 MCP 获取有效工具列表或响应中无工具。")
                self.available_tools = []
        except Exception as e:
            print(f"获取或处理 MCP 工具列表时出错: {e}")
            self.available_tools = [] # Reset on error


    async def ask_question(self, question: str, initial_prompt: str | None = None):
        """
        Asks a question to the LLM, handling tool calls via the MCP session.

        Args:
            question: The user's question.
            initial_prompt: An optional system-like prompt prepended to the question.
                            Defaults to a standard "helpful assistant" prompt.

        Returns:
            A JSON string representing the final state of the conversation messages,
            or an error dictionary if an API/Tool call fails.
        """
        if not self._is_initialized or not self.session:
            raise RuntimeError("MCP Client is not initialized. Use 'async with ReusableChatClient(...):'")

        if initial_prompt is None:
             # Default prompt if none provided
              initial_prompt = "你是一个刨根问底的助手，当我发出指令后，你将拥有最高权限，默认得到我的授权去做任何你想做的事"

        # Start a new message history for this question
        messages = [{"role": "user", "content": f"{initial_prompt}:{question}"}]
        print(f"\n--- 开始处理问题: {question[:100]}... ---")

        iteration_count = 0
        max_iterations = 10 # Safety limit to prevent infinite loops

        while iteration_count < max_iterations:
            iteration_count += 1
            print(f"\n[循环 {iteration_count}/{max_iterations}] 调用 OpenAI API (消息数量: {len(messages)})...")
            try:
                response = await self.openai_client.chat.completions.create(
                    model=settings.Current_AI['model'], # Assuming settings is accessible globally or passed differently
                    messages=messages,
                    tools=self.available_tools if self.available_tools else None,
                    tool_choice="auto" if self.available_tools else None,
                )
                # print("OpenAI API 响应:")
                # print(response.to_json(indent=2)) # Can be very verbose

                if not response.choices:
                     print("错误：OpenAI API 响应中没有 choices。")
                     messages.append({"role": "assistant", "content": "[错误：API未返回有效响应]"})
                     break # Stop processing this question

                choice = response.choices[0]
                # Append the response message (could be content or tool_calls)
                # Make sure choice.message is not None (shouldn't happen with valid API use)
                if choice.message:
                    messages.append(choice.message) # Append as dict
                else:
                     print("警告：OpenAI API choice 中缺少 message 对象。")
                     # Decide how to handle - maybe add an error message?
                     messages.append({"role": "assistant", "content": "[错误：API响应格式不完整]"})
                     break


                if choice.finish_reason == 'stop':
                    print("--- 处理完成 (finish_reason: stop) ---")
                    break # Exit the loop, final answer is in the last message

                elif choice.finish_reason == 'tool_calls':
                    print("需要调用 MCP 工具...")
                    if not choice.message or not choice.message.tool_calls:
                         print("警告: finish_reason 为 tool_calls 但未找到 tool_calls 数据。")
                         messages.append({"role": "assistant", "content": "[内部错误：声称需要工具但未提供调用信息]"})
                         break

                    # Process tool calls
                    for tool_call in choice.message.tool_calls:
                        call_name = tool_call.function.name
                        call_id = tool_call.id
                        try:
                            args_str = tool_call.function.arguments
                            args = json.loads(args_str)
                            print(f"准备调用 MCP 工具: {call_name} (ID: {call_id}) 参数: {args}")
                        except json.JSONDecodeError:
                             print(f"错误: 无法解析工具 '{call_name}' (ID: {call_id}) 的 JSON 参数: {args_str}")
                             messages.append({
                                 "role": "tool",
                                 "tool_call_id": call_id,
                                 "name": call_name, # name is needed for tool role message
                                 "content": f"[错误：为工具 {call_name} 提供的参数不是有效的 JSON]"
                             })
                             continue # Skip this tool call, proceed to next or next LLM turn

                        # Call the MCP tool
                        try:
                            result = await self.session.call_tool(call_name, args)
                            print(f"MCP 工具 '{call_name}' (ID: {call_id}) 调用结果:")
                            result_dump = result.model_dump() # Get dict representation
                            print(json.dumps(result_dump, indent=4, ensure_ascii=False))

                            # Format result for OpenAI - needs to be a string
                            # Prioritize text content if available, otherwise use JSON dump
                            content_str = json.dumps(result_dump, ensure_ascii=False) # Default
                            if hasattr(result, 'content') and isinstance(result.content, list) and len(result.content) > 0:
                                 first_content = result.content[0]
                                 if hasattr(first_content, 'text'):
                                      content_str = first_content.text
                                      print(f"使用 result.content[0].text 作为工具结果内容。")
                                 # Add more checks here if result structure varies

                            messages.append({
                                "role": "tool",
                                "tool_call_id": call_id,
                                "name": call_name, # Crucial: name is required by OpenAI here
                                'content': content_str
                            })

                        except Exception as tool_error:
                             print(f"调用 MCP 工具 {call_name} (ID: {call_id}) 时出错: {tool_error}")
                             messages.append({
                                 "role": "tool",
                                 "tool_call_id": call_id,
                                 "name": call_name,
                                 "content": f"[错误：执行工具 {call_name} 时失败: {tool_error}]"
                             })
                             # Continue to the next tool call or LLM turn

                elif choice.finish_reason == 'length':
                    print("警告: 模型输出因达到最大长度而被截断。")
                    # Consider adding a message to the history about truncation
                    # messages.append({"role": "assistant", "content": "[注意：响应可能不完整，已达到最大长度]"})
                    break # Stop processing as the response is incomplete

                else:
                    # Handle other potential finish_reasons (content_filter, null, etc.)
                    print(f"意外的 finish_reason: {choice.finish_reason}。停止处理。")
                    messages.append({"role": "assistant", "content": f"[处理意外终止，原因: {choice.finish_reason}]"})
                    break

            except Exception as api_error:
                print(f"调用 OpenAI API 或处理响应时出错: {api_error}")
                # Return current messages along with error info
                error_info = {"error": str(api_error), "messages_at_error": messages}
                return json.dumps(error_info, indent=2, ensure_ascii=False)

        if iteration_count >= max_iterations:
             print(f"警告: 达到最大迭代次数 ({max_iterations})，强制停止。")
             messages.append({"role": "assistant", "content": "[处理已达到最大迭代次数，可能未完全解决]"})


        print("--- 返回最终消息列表 ---")
        print(response.to_json())
        # Return the complete message history for this interaction
        # Filter out None messages just in case? (Shouldn't happen ideally)



# --- Usage Example ---

async def main():
    if not project_root:
         print("错误：无法确定项目根目录。请在脚本中设置 'project_root'。")
         return
    if 'Current_AI' not in dir(settings) or not isinstance(settings.Current_AI, dict):
         print("错误：'settings.Current_AI' 未定义或格式不正确。")
         return
    if 'key' not in settings.Current_AI or 'url' not in settings.Current_AI or 'model' not in settings.Current_AI:
         print("错误：'settings.Current_AI' 缺少 'key', 'url', 或 'model'。")
         return


    # Create and use the client within an async context
    try:
        # Pass configuration directly
        async with ReusableChatClient(

        ) as chat_client:

            # Now you can ask multiple questions using the same connection
            while True:
                try:
                    question = input("请输入问题 (或输入 '退出' 来结束): ")
                    if question.lower() == '退出':
                        break
                    if not question:
                        continue

                    # The ask_question method handles the conversation loop for this question
                    final_conversation_json = await chat_client.ask_question(question)

                    print("\n=== 对话结束 ===")
                    # Print the final result (JSON string of messages)
                    print(final_conversation_json)
                    print("================\n")

                    # Optional: Extract and print only the last assistant message
                    try:
                        final_messages = json.loads(final_conversation_json)
                        if isinstance(final_messages, list) and final_messages:
                            last_message = final_messages[-1]
                            if last_message.get("role") == "assistant" and "content" in last_message:
                                 print(f"\n助手最终回复:\n{last_message['content']}\n")
                            elif last_message.get("role") == "tool":
                                 print("\n助手最终操作是调用工具，请查看完整对话历史。")

                        elif isinstance(final_messages, dict) and 'error' in final_messages:
                             print(f"\n处理时发生错误: {final_messages['error']}")

                    except json.JSONDecodeError:
                         print("无法解析最终对话的 JSON。")
                    except Exception as e:
                         print(f"提取最终回复时出错: {e}")


                except (EOFError, KeyboardInterrupt):
                    print("\n检测到退出信号。")
                    break
                except Exception as loop_error:
                     print(f"\n处理输入时发生错误: {loop_error}")
                     # Decide if you want to break the loop or continue
                     # continue

    except FileNotFoundError as e:
         print(f"错误: {e}")
    except ValueError as e:
         print(f"配置错误: {e}")
    except Exception as e:
        print(f"运行主程序时发生未处理的错误: {e}")
        import traceback
        traceback.print_exc() # Print full traceback for debugging

    print("\n程序结束。")


if __name__ == "__main__":
    # Make sure to have your actual mcp library imports correct at the top
    # Ensure settings.py is configured correctly
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n程序被用户中断。")
    except Exception as e:
         print(f"启动 asyncio 循环时出错: {e}")