CALL="bash ebo_call.sh"; id=1
for round in $(seq 1 10); do
$CALL $id robot_speak '{"text":"起床啦！起床啦！","lang":"zh-CN"}'; id=$((id+1))
sleep 25
st=$($CALL $id robot_status '{}'); id=$((id+1))
echo "$st"
detected=$(printf '%s' "$st" | python -c 'import sys,json,re; t=json.load(sys.stdin)["result"]["content"][0]["text"]; m=re.search(r"当前检测到人数：(\d+)",t); n=int(m.group(1)) if m else 0; v=re.search(r"camera view[^\n]*: (.*)",t); view=(v.group(1).strip() if v else ""); print("yes" if (n>0 or (view and view.lower()!="none")) else "no")')
[ "$detected" = "yes" ] && { echo "第 $round 轮检测到人"; break; }
done
