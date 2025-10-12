import json
from pathlib import Path

# 找到最新的JSON文件
recordings_dir = Path("elevator_saga/visualization/recordings")
json_files = sorted(recordings_dir.glob("optimal_look_*.json"), key=lambda x: x.stat().st_mtime, reverse=True)

if not json_files:
    print("No JSON files found")
    exit()

# 分析最新的JSON文件
json_file = json_files[0]
print(f"Analyzing: {json_file.name}")
print("=" * 60)

with open(json_file, encoding='utf-8') as f:
    data = json.load(f)

print(f"Total ticks: {data['metadata']['total_ticks']}")
print(f"Algorithm: {data['metadata']['algorithm']}")

# 统计所有乘客
all_passengers = set()
board_count = 0
alight_count = 0
call_count = 0

for h in data['history']:
    all_passengers.update(h['passengers'].keys())
    for e in h['events']:
        if e['type'] == 'passenger_board':
            board_count += 1
        elif e['type'] == 'passenger_alight':
            alight_count += 1
        elif e['type'] in ['up_button_pressed', 'down_button_pressed']:
            call_count += 1

print(f"\nTotal unique passengers: {len(all_passengers)}")
print(f"Passenger call events: {call_count}")
print(f"Board events: {board_count}")
print(f"Alight events: {alight_count}")

# 最终状态
final_state = data['history'][-1]
print(f"\nFinal passengers in system: {len(final_state['passengers'])}")
if final_state['passengers']:
    completed = sum(1 for p in final_state['passengers'].values() if p['status'] == 'completed')
    in_elevator = sum(1 for p in final_state['passengers'].values() if p['status'] == 'in_elevator')
    waiting = sum(1 for p in final_state['passengers'].values() if p['status'] == 'waiting')
    print(f"  Completed: {completed}")
    print(f"  In elevator: {in_elevator}")
    print(f"  Waiting: {waiting}")

# 性能指标
metrics = final_state['metrics']
print(f"\nPerformance Metrics:")
print(f"  Completed passengers: {metrics.get('completed_passengers', 0)}")
print(f"  Average wait time: {metrics.get('average_wait_time', 0):.2f} ticks")
print(f"  P95 wait time: {metrics.get('p95_wait_time', 0):.2f} ticks")
print(f"  Average system time: {metrics.get('average_system_time', 0):.2f} ticks")

# 检查中间状态
print(f"\n检查中间状态 (tick {len(data['history'])//2}):")
mid_state = data['history'][len(data['history'])//2]
print(f"  Passengers in system: {len(mid_state['passengers'])}")
if mid_state['passengers']:
    for p_id, p_info in list(mid_state['passengers'].items())[:5]:
        print(f"    P{p_id}: {p_info['origin']}->{p_info['destination']}, status={p_info['status']}")

# 检查楼层队列
print(f"\n楼层队列状态:")
for floor_info in mid_state['floors']:
    if floor_info['up_queue'] or floor_info['down_queue']:
        print(f"  F{floor_info['floor']}: up={floor_info['up_queue']}, down={floor_info['down_queue']}")

# 检查电梯状态
print(f"\n电梯状态:")
for elev_info in mid_state['elevators']:
    print(f"  E{elev_info['id']}: F{elev_info['current_floor']:.1f} -> F{elev_info['target_floor']}, " +
          f"dir={elev_info['direction']}, status={elev_info['status']}, " +
          f"passengers={elev_info['passengers']}")

# 检查stopped_at_floor事件
print(f"\n检查STOPPED事件 (前20个):")
stopped_count = 0
for h in data['history'][:100]:
    for e in h['events']:
        if e['type'] == 'stopped_at_floor':
            print(f"  Tick {h['tick']}: E{e['data'].get('elevator_id')} stopped at F{e['data'].get('floor')}")
            stopped_count += 1
            if stopped_count >= 20:
                break
    if stopped_count >= 20:
        break
