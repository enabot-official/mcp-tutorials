def speak_time(begin_time: str) -> str:
    hh, mm = begin_time[11:13], begin_time[14:16]
    h = int(hh)
    if h <= 5:    period = f"凌晨{h}点"
    elif h <= 11: period = f"上午{h}点"
    elif h == 12: period = "中午12点"
    elif h <= 18: period = f"下午{h-12}点"
    else:         period = f"晚上{h-12}点"
    return period if int(mm) == 0 else f"{period}{int(mm)}分"

    # 10:00 -> 上午10点 ; 14:30 -> 下午2点30分 ; 15:00 -> 下午3点
