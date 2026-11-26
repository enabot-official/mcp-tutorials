CALL="bash ebo_call.sh"; id=1
$CALL $id robot_stop_patrol '{"lang":"zh-CN"}'; id=$((id+1))
$CALL $id robot_go_home '{"startUp":true,"lang":"zh-CN"}'; id=$((id+1))
for poll in $(seq 1 6); do
sleep 40
st=$($CALL $id robot_status '{}'); id=$((id+1))
echo "$st" | grep -q "充电桩充电中" && echo "$st" | grep -q "设备任务：空闲" && { echo "回桩成功"; break; }
done
