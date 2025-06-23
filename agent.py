"""
agent_actionstack.py  (v4)
────────────────────────────────────────────────────────────────────────────
• 주요 변경
  1. _nearest_safe : 탐험 단계에서는 이미 방문한 (1,1)을 목표로 삼지 않음
  2. _plan         : 방문 safe 가 고갈되면 unknown 으로 즉시 전환
  3. 나머지 로직(v3) : Grab-TurnLeft×2, 행동 스택 역추적, 3-회 사격 서열 등
────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Set, Tuple, List, Optional, Deque
from collections import deque

from setting import Dir, Percept, World, SAFE_STARTS


# ──────────────────────────────────────────────────────────────────────────
@dataclass
class Agent:
    # ── 1. 위치 · 상태 ───────────────────────────────────────────
    world: World
    x: int = 1
    y: int = 1
    dir: Dir = Dir.E
    arrows: int = 3
    has_gold: bool = False
    performance: int = 0

    # ── 2. 지식 베이스 ─────────────────────────────────────────
    visited: Set[Tuple[int, int]] = field(default_factory=set)
    safe: Set[Tuple[int, int]] = field(default_factory=lambda: {(1, 1), (1, 2), (2, 1)})
    definite_pit: Set[Tuple[int, int]] = field(default_factory=set)
    definite_wumpus: Set[Tuple[int, int]] = field(default_factory=set)
    definite_obstacle: Set[Tuple[int, int]] = field(default_factory=set)

    stench_dirs: Set[Dir] = field(default_factory=set)
    breeze_cells: List[Tuple[int, int]] = field(default_factory=list)

    # ── 3. 제어 플래그 ─────────────────────────────────────────
    returning: bool = False
    pending_shot: Optional[Dir] = None
    turn_after_shoot: bool = False
    force_forward: bool = False
    forced_turns: int = 0           # Grab 후 남은 강제 TurnLeft 횟수
    shoot_stage: int = 0            # Wumpus 사격 단계 (0~5)

    prev: Tuple[int, int] = (1, 1)
    prev_dir: Optional[Dir] = None
    spin_count: int = 0

    start_targets: Deque[Tuple[int, int]] = field(default_factory=lambda: deque([(2, 1), (1, 2)]))

    # ── 4. 행동 스택 ───────────────────────────────────────────
    visit_act: List[str] = field(default_factory=list)
    pop_idx: int = -1

    history: List[dict] = field(default_factory=list)

    # ──────────────────────────────────────────────────────────
    #  로그 헬퍼
    # ──────────────────────────────────────────────────────────
    def _log(self, step: int, act: str, p: Percept):
        self.history.append(dict(step=step, act=act,
                                 pos=(self.x, self.y),
                                 dir=self.dir.name, percept=repr(p)))

    # ──────────────────────────────────────────────────────────
    #  탐색 유틸리티
    # ──────────────────────────────────────────────────────────
    def _best_unknown(self) -> Optional[Tuple[int, int]]:
        best, score = None, -1.0
        for x in range(1, 5):
            for y in range(1, 5):
                pos = (x, y)
                if pos in self.visited | self.safe | self.definite_pit | \
                   self.definite_wumpus | self.definite_obstacle:
                    continue
                adj = [(x + d.dx, y + d.dy) for d in Dir]
                safe_ratio = sum(1 for a in adj if a in self.safe) / 4
                near_breeze = any(abs(x - bx) + abs(y - by) == 1
                                  for bx, by in self.breeze_cells)
                val = safe_ratio + (0.5 if near_breeze else 0)
                if val > score:
                    best, score = pos, val
        return best

    def _nearest_safe(self) -> Optional[Tuple[int, int]]:
        """아직 방문하지 않은 safe. returning 상태에서만 (1,1)을 허용"""
        for p in sorted(self.safe,
                        key=lambda t: abs(t[0] - self.x) + abs(t[1] - self.y)):
            if p == (1, 1) and not self.returning:     # ★ 변경
                continue
            if p not in self.visited and p != (self.x, self.y) and p != self.prev:
                return p
        return None

    def _move(self, tgt: Optional[Tuple[int, int]]) -> str:
        if tgt is None:
            return "TurnLeft"
        if tgt != (1, 1) and tgt in (self.definite_pit |
                                     self.definite_wumpus |
                                     self.definite_obstacle):
            return "TurnLeft"
        if (self.x + self.dir.dx, self.y + self.dir.dy) == tgt:
            return "Forward"

        dx, dy = tgt[0] - self.x, tgt[1] - self.y
        desired = (Dir.E if dx > 0 else Dir.W if dx < 0 else
                   Dir.N if dy > 0 else Dir.S)
        if self.dir == desired:
            return "Forward"
        order = [Dir.N, Dir.E, Dir.S, Dir.W]
        return "TurnRight" if (order.index(desired) - order.index(self.dir)) % 4 == 1 \
                           else "TurnLeft"

    def _plan(self, tgt: Optional[Tuple[int, int]]) -> str:
        if tgt and tgt != (self.x, self.y):
            return self._move(tgt)
        alt = self._nearest_safe()
        if alt:
            return self._move(alt)
        # safe 모두 방문 → unknown 으로 ★ 변경
        unk = self._best_unknown()
        return self._move(unk)

    # ──────────────────────────────────────────────────────────
    #  KB 업데이트 (기존 로직 그대로)
    # ──────────────────────────────────────────────────────────
    def _update(self, p: Percept):
        self.visited.add((self.x, self.y)); self.safe.add((self.x, self.y))
        if not p.stench and not p.breeze:
            for d in Dir:
                ax, ay = self.x + d.dx, self.y + d.dy
                if 1 <= ax <= 4 and 1 <= ay <= 4:
                    self.safe.add((ax, ay))
        if p.stench:
            for d in Dir:
                nx, ny = self.x + d.dx, self.y + d.dy
                if 1 <= nx <= 4 and 1 <= ny <= 4:
                    self.stench_dirs.add(d)
        if p.breeze:
            self.breeze_cells.append((self.x, self.y))
            if len(self.breeze_cells) >= 2:
                inter = set.intersection(*[
                    {(bx + d.dx, by + d.dy)
                     for d in Dir if 1 <= bx + d.dx <= 4 and 1 <= by + d.dy <= 4}
                    for bx, by in self.breeze_cells])
                for pt in inter:
                    if pt not in SAFE_STARTS:
                        self.definite_pit.add(pt); self.safe.discard(pt)
        if p.scream:
            self.stench_dirs.clear(); self.pending_shot = None; self.force_forward = True

    # ──────────────────────────────────────────────────────────
    #  의사결정
    # ──────────────────────────────────────────────────────────
    def _decide(self, p: Percept) -> str:
        # 보정 플래그
        if self.force_forward:
            self.force_forward = False
            return "Forward"
        if self.turn_after_shoot:
            self.turn_after_shoot = False
            return "TurnLeft"

        # 귀환 모드
        if self.returning:
            if self.forced_turns > 0:
                self.forced_turns -= 1
                return "TurnLeft"
            if (self.x, self.y) == (1, 1) and self.pop_idx < 0:
                return "Climb"
            if self.pop_idx >= 0:
                rev = self.visit_act[self.pop_idx]; self.pop_idx -= 1
                return {"F": "Forward", "L": "TurnRight", "R": "TurnLeft"}[rev]
            return "TurnLeft"

        # 정면 위험 회피
        ahead = (self.x + self.dir.dx, self.y + self.dir.dy)
        if ahead in (self.definite_pit | self.definite_wumpus | self.definite_obstacle):
            return "TurnLeft"

        # 탐험 모드
        if p.glitter:
            return "Grab"
        if p.breeze:
            return "Forward"

        # 스텐치 3-회 사격 시퀀스
        if p.stench and self.arrows > 0:
            if self.shoot_stage == 0:
                self.pending_shot = self.dir; self.shoot_stage = 1; return "Shoot"
            elif self.shoot_stage == 1:
                self.shoot_stage = 2; return "TurnLeft"
            elif self.shoot_stage == 2:
                self.pending_shot = self.dir; self.shoot_stage = 3; return "Shoot"
            elif self.shoot_stage == 3:
                self.shoot_stage = 4; return "TurnLeft"
            elif self.shoot_stage == 4:
                self.shoot_stage = 5; return "TurnLeft"
            else:  # 5
                self.pending_shot = self.dir; self.shoot_stage = 0; return "Shoot"

        if ((self.x, self.y) == (1, 1) and not self._nearest_safe() and
                not self._best_unknown() and not self.stench_dirs):
            return "Climb"

        return self._plan(self._nearest_safe())

    # ──────────────────────────────────────────────────────────
    #  한 턴 실행
    # ──────────────────────────────────────────────────────────
    def step(self, step: int) -> bool:
        self.performance -= 1
        p = self.world.get_percept(self.x, self.y)
        self._update(p)
        act = self._decide(p)

        # 회전 루프 방지
        if act in ("TurnLeft", "TurnRight"):
            self.spin_count += 1
            if self.spin_count >= 4:
                self.spin_count = 0
                ax, ay = self.x + self.dir.dx, self.y + self.dir.dy
                act = "TurnRight" if self.world.grid[ay][ax] == "W" else "Forward"
        else:
            self.spin_count = 0

        # ── 실제 행동 실행 ────────────────────────────────────
        if act == "Forward":
            if not self.returning:
                self.visit_act.append("F")
            self.prev_dir = self.dir.right().right()
            nx, ny, newp = self.world.forward(self.x, self.y, self.dir)
            ahead = (self.x + self.dir.dx, self.y + self.dir.dy)
            if newp.bump:
                self.definite_obstacle.add(ahead)
            else:
                self.x, self.y = nx, ny
            p |= newp

        elif act == "TurnLeft":
            if not self.returning:
                self.visit_act.append("L")
            self.dir = self.dir.left()

        elif act == "TurnRight":
            if not self.returning:
                self.visit_act.append("R")
            self.dir = self.dir.right()

        elif act == "Grab":
            self.has_gold = True
            self.returning = True
            self.forced_turns = 2
            self.pop_idx = len(self.visit_act) - 1
            self.world.tile_state[self.y][self.x]["gold"] = False

        elif act == "Shoot" and self.pending_shot:
            d = self.pending_shot
            self.pending_shot = None
            self.arrows -= 1
            p.scream = self.world.shoot(self.x, self.y, d)

            # ──────────────────────────────────────────────
            #  명중 시 → 다음 턴 전진
            #  빗나감 시 → 시퀀스 사격이면 turn_after_shoot 생략
            # ──────────────────────────────────────────────
            if p.scream:
                self.force_forward = True
            else:
                if self.shoot_stage == 0:
                    self.turn_after_shoot = True


        elif act == "Climb":
            if self.has_gold:
                self.performance += 1000
            self._log(step, act, p)
            return False

        # 사망 판정
        dead = (self.world.tile_has_pit(self.x, self.y) or
                self.world.tile_has_live_wumpus(self.x, self.y))
        if dead:
            self.performance -= 30
            self.visit_act.clear(); self.returning = False
            self.pop_idx = -1; self.shoot_stage = 0; self.forced_turns = 0
            if self.world.tile_has_pit(self.x, self.y):
                self.definite_pit.add((self.x, self.y))
            if self.world.tile_has_live_wumpus(self.x, self.y):
                self.definite_wumpus.add((self.x, self.y))
            self.safe.discard((self.x, self.y))

        # 로그
        self._log(step, act if not dead else act + "(DEAD)", p)
        self.prev = (self.x, self.y)
        return not dead

    # ──────────────────────────────────────────────────────────
    #  리셋 & 기록 출력
    # ──────────────────────────────────────────────────────────
    def reset_position(self):
        self.x, self.y, self.dir = 1, 1, Dir.E
        self.arrows = 3; self.has_gold = False; self.performance = 0
        self.returning = False; self.pending_shot = None
        self.turn_after_shoot = False; self.force_forward = False
        self.forced_turns = 0; self.shoot_stage = 0
        self.prev = (1, 1); self.prev_dir = None; self.spin_count = 0
        self.visit_act.clear(); self.pop_idx = -1

    def print_history(self):
        print("\n===== Trace =====")
        for h in self.history:
            print(f"{h['step']:03d} | {h['act']:<14} | Pos{h['pos']} | "
                  f"Dir {h['dir']:<2} | {h['percept']}")
        print("================================================")
