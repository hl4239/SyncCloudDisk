from datetime import date

def weekday_cn(d: date) -> str:
    """返回中文星期几"""
    WEEKDAY_CN = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    return WEEKDAY_CN[d.weekday()]
