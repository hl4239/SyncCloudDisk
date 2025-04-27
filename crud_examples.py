from sqlmodel import Session, SQLModel, create_engine, select
from models.resource import Resource, ResourceCategory # 导入模型和枚举
from database import engine, create_db_and_tables # 导入引擎和创建函数

# --- 创建资源 (Create) ---
def create_resource(session: Session, title: str, category: ResourceCategory, storage_path: str, description: str | None = None, total_episodes: int | None = None, updated_episodes: int = 0, image_path: str | None = None, tags: list[str] | None = None) -> Resource:
    """创建一个新的影视资源记录"""
    print(f"Creating resource: {title}")
    resource = Resource(
        title=title,
        description=description,
        category=category,
        storage_path=storage_path,
        total_episodes=total_episodes,
        updated_episodes=updated_episodes,
        image_path=image_path,
        tags=tags or [] # 确保 tags 是列表
    )
    session.add(resource)
    session.commit()
    session.refresh(resource) # 获取数据库生成的 ID 等信息
    print(f"Resource created successfully with ID: {resource.id}")
    return resource

# --- 读取资源 (Read) ---
def get_resource_by_id(session: Session, resource_id: int) -> Resource | None:
    """根据 ID 获取单个资源"""
    print(f"Getting resource by ID: {resource_id}")
    resource = session.get(Resource, resource_id)
    if resource:
        print(f"Found resource: {resource.title}")
    else:
        print(f"Resource with ID {resource_id} not found.")
    return resource

def get_resources(session: Session, offset: int = 0, limit: int = 10) -> list[Resource]:
    """获取资源列表（分页）"""
    print(f"Getting resources (offset={offset}, limit={limit})")
    statement = select(Resource).offset(offset).limit(limit)
    results = session.exec(statement).all()
    print(f"Found {len(results)} resources.")
    return results

def get_resources_by_category(session: Session, category: ResourceCategory) -> list[Resource]:
    """根据分类获取资源列表"""
    print(f"Getting resources by category: {category.value}")
    statement = select(Resource).where(Resource.category == category)
    results = session.exec(statement).all()
    print(f"Found {len(results)} resources in category {category.value}.")
    return results

# --- 更新资源 (Update) ---
def update_resource_episodes(session: Session, resource_id: int, new_updated_episodes: int) -> Resource | None:
    """更新资源的已更新集数"""
    print(f"Updating episodes for resource ID: {resource_id}")
    resource = session.get(Resource, resource_id)
    if resource:
        resource.updated_episodes = new_updated_episodes
        session.add(resource)
        session.commit()
        session.refresh(resource)
        print(f"Resource ID {resource_id} updated episodes to {new_updated_episodes}.")
        return resource
    else:
        print(f"Resource with ID {resource_id} not found for update.")
        return None

def update_resource_description(session: Session, resource_id: int, new_description: str) -> Resource | None:
    """更新资源的描述"""
    print(f"Updating description for resource ID: {resource_id}")
    resource = session.get(Resource, resource_id)
    if resource:
        resource.description = new_description
        session.add(resource)
        session.commit()
        session.refresh(resource)
        print(f"Resource ID {resource_id} description updated.")
        return resource
    else:
        print(f"Resource with ID {resource_id} not found for update.")
        return None

# --- 删除资源 (Delete) ---
def delete_resource(session: Session, resource_id: int) -> bool:
    """根据 ID 删除资源"""
    print(f"Deleting resource ID: {resource_id}")
    resource = session.get(Resource, resource_id)
    if resource:
        session.delete(resource)
        session.commit()
        print(f"Resource ID {resource_id} deleted successfully.")
        return True
    else:
        print(f"Resource with ID {resource_id} not found for deletion.")
        return False

# --- 示例用法 ---
if __name__ == "__main__":
    # 重要提示：在运行此示例之前，请确保已执行 python database.py 创建了数据库和表
    # 或者，您可以取消下面这行注释，让脚本在运行时自动创建（如果不存在）
    # create_db_and_tables()

    print("\n--- Starting CRUD Examples ---")

    with Session(engine) as session:
        # 1. 创建资源
        print("\n--- CREATE ---")
        drama1 = create_resource(
            session=session,
            title="繁花",
            category=ResourceCategory.HOT_CN_DRAMA,
            storage_path="/mnt/share/dramas/繁花",
            description="九十年代上海的故事",
            total_episodes=30,
            updated_episodes=30,
            tags=["剧情", "年代"]
        )
        anime1 = create_resource(
            session=session,
            title="鬼灭之刃",
            category=ResourceCategory.HOT_ANIME,
            storage_path="/mnt/share/anime/鬼灭之刃",
            total_episodes=55, # 假设总集数
            updated_episodes=20,
            tags=["热血", "奇幻", "战斗"]
        )
        drama2 = create_resource(
            session=session,
            title="庆余年 第二季",
            category=ResourceCategory.HOT_CN_DRAMA,
            storage_path="/mnt/share/dramas/庆余年2",
            total_episodes=36,
            updated_episodes=5,
            tags=["古装", "权谋", "爽文"]
        )

        # 2. 读取资源
        print("\n--- READ ---")
        # 按 ID 获取
        get_resource_by_id(session, drama1.id)
        get_resource_by_id(session, 999) # 尝试获取不存在的 ID

        # 获取所有资源（前 10 条）
        all_resources = get_resources(session)
        for res in all_resources:
            print(f"  - ID: {res.id}, Title: {res.title}, Category: {res.category.value}")

        # 按分类获取
        cn_dramas = get_resources_by_category(session, ResourceCategory.HOT_CN_DRAMA)
        for res in cn_dramas:
            print(f"  - CN Drama: {res.title}")

        # 3. 更新资源
        print("\n--- UPDATE ---")
        # 更新集数
        update_resource_episodes(session, anime1.id, 26) # 假设更新到 26 集
        # 更新描述
        update_resource_description(session, drama1.id, "九十年代上海的商业故事和个人奋斗。")

        # 再次获取以查看更新
        updated_anime = get_resource_by_id(session, anime1.id)
        if updated_anime:
            print(f"  - Updated Anime Episodes: {updated_anime.updated_episodes}")
        updated_drama = get_resource_by_id(session, drama1.id)
        if updated_drama:
            print(f"  - Updated Drama Description: {updated_drama.description}")


        # 4. 删除资源
        print("\n--- DELETE ---")
        # 假设我们想删除 "庆余年 第二季" (测试用)
        delete_resource(session, drama2.id)
        # 尝试再次获取已删除的资源
        get_resource_by_id(session, drama2.id)

        # 再次获取所有资源，确认已删除
        print("\n--- Final Resource List ---")
        final_resources = get_resources(session)
        for res in final_resources:
            print(f"  - ID: {res.id}, Title: {res.title}")

    print("\n--- CRUD Examples Finished ---")