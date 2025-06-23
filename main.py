import argparse
from setting import World
from agent   import Agent


def print_world_debug(world: World):
    print("\n📍 초기 맵 -----------------------------")
    for y in range(4, 0, -1):
        row = []
        for x in range(1, 5):
            if   (x, y) == world.gold_xy: row.append("G")
            elif (x, y) in world.wumpi:   row.append("U")
            elif (x, y) in world.pits:    row.append("P")
            else:                         row.append(".")
        print(f"{y} | " + " ".join(row))
    print("    1 2 3 4")
    print(f"Gold:{world.gold_xy}  Wumpus:{sorted(world.wumpi)}  Pits:{sorted(world.pits)}\n")


def main(seed=None, limit=120):
    world = World(seed)
    print_world_debug(world)

    ag = Agent(world)
    deaths = 0
    for step in range(1, limit + 1):
        alive = ag.step(step)
        if alive and ag.has_gold and (ag.x, ag.y) == (1, 1):
            break
        if not alive:
            deaths += 1
            ag.reset_position()

    ag.print_history()
    print(f"\n총 이동  : {len(ag.history)}")
    print(f"죽은 횟수: {deaths}")
    print(f"점수     : {ag.performance}")
    print("성공" if ag.has_gold and (ag.x, ag.y) == (1, 1) else "실패")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, help="랜덤 시드")
    ap.add_argument("--limit", type=int, default=120, help="최대 스텝 수")
    args = ap.parse_args()
    main(args.seed, args.limit)
