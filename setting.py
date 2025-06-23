from __future__ import annotations
from dataclasses import dataclass, field
from typing import Tuple, Set, List, Dict, Optional
import enum, random, time

# ─────────────────── Direction ───────────────────
class Dir(enum.Enum):
    E = (1, 0); S = (0, -1); W = (-1, 0); N = (0, 1)
    def left (self):  return {Dir.E:Dir.N, Dir.N:Dir.W, Dir.W:Dir.S, Dir.S:Dir.E}[self]
    def right(self):  return {Dir.E:Dir.S, Dir.S:Dir.W, Dir.W:Dir.N, Dir.N:Dir.E}[self]
    @property
    def dx(self): return self.value[0]
    @property
    def dy(self): return self.value[1]

# ─────────────────── Percept ─────────────────────
@dataclass
class Percept:
    stench: bool=False; breeze: bool=False; glitter: bool=False
    bump:   bool=False; scream: bool=False
    def __ior__(self,o:'Percept'):
        self.stench|=o.stench; self.breeze|=o.breeze
        self.glitter|=o.glitter; self.bump|=o.bump; self.scream|=o.scream; return self
    def __repr__(self):
        return (f"S:{int(self.stench)} B:{int(self.breeze)} "
                f"G:{int(self.glitter)} Bu:{int(self.bump)} Sc:{int(self.scream)}")

# ─────────────────── World ───────────────────────
WALL,PIT,WUMPUS,GOLD,EMPTY = "W","P","U","G","."
SAFE_STARTS={(1,1),(1,2),(2,1)}

@dataclass
class World:
    seed: Optional[int]=None
    size:int=field(init=False,default=6)                 # 0,5 (벽포함)

    pits:  Set[Tuple[int,int]]=field(init=False,default_factory=set)
    wumpi: Set[Tuple[int,int]]=field(init=False,default_factory=set)
    gold_xy: Tuple[int,int]=field(init=False)
    tile_state: List[List[Dict[str,int|bool]]]=field(init=False)

    wumpus_alive: bool=field(init=False,default=True)

    def __post_init__(self):
        random.seed(self.seed if self.seed is not None else time.time_ns()&0xFFFFFFFF)
        self._generate()

    # ───────── 지도 생성 ─────────
    def _generate(self):
        # 격자 (벽)
        self.grid=[[WALL]*self.size for _ in range(self.size)]
        for y in range(1,5):
            for x in range(1,5):
                self.grid[y][x]=EMPTY

        # 확률 배치: pit,wumpus <3, 한 칸 겹침 금지
        for x in range(1,5):
            for y in range(1,5):
                if (x,y) in SAFE_STARTS: continue
                if random.random()<0.1 and len(self.wumpi)<2:
                    self.wumpi.add((x,y))
                if random.random()<0.1 and len(self.pits)<2 and (x,y) not in self.wumpi:
                    self.pits.add((x,y))
        # Gold 1개
        cand=[(x,y) for x in range(1,5) for y in range(1,5)
              if (x,y) not in SAFE_STARTS|self.wumpi|self.pits]
        self.gold_xy=random.choice(cand)

        # 타일 메타데이터
        self.tile_state=[[{
            'stench':0,'breeze':0,
            'pit':(x,y) in self.pits,
            'wumpus':(x,y) in self.wumpi,
            'gold':(x,y)==self.gold_xy
        } for x in range(self.size)] for y in range(self.size)]

        for wx,wy in self.wumpi: self._adjust_stench(wx,wy,+1)
        for px,py in self.pits:  self._adjust_breeze(px,py,+1)

    # ───────── 감각 ─────────
    def get_percept(self,x:int,y:int)->Percept:
        t=self.tile_state[y][x]
        return Percept(stench=t['stench']>0, breeze=t['breeze']>0, glitter=t['gold'])

    # ───────── 이동 ─────────
    def forward(self,x:int,y:int,d:Dir):
        nx,ny=x+d.dx,y+d.dy
        if self.grid[ny][nx]==WALL:
            p=self.get_percept(x,y); p.bump=True
            return x,y,p
        p=self.get_percept(nx,ny)
        return nx,ny,p

    # ───────── 사격 ─────────
    def shoot(self,x:int,y:int,d:Dir)->bool:
        cx,cy=x+d.dx,y+d.dy
        while self.grid[cy][cx]!=WALL:
            if (cx,cy) in self.wumpi:
                self.wumpi.remove((cx,cy))
                self._adjust_stench(cx,cy,-1)      # <- 스텐치 감소!
                if not self.wumpi: self.wumpus_alive=False
                return True
            cx+=d.dx; cy+=d.dy
        return False

    # ───────── 위험 체크 ─────────
    def tile_has_pit(self,x,y):         return (x,y) in self.pits
    def tile_has_live_wumpus(self,x,y): return (x,y) in self.wumpi

    # ───────── 내부 유틸 ─────────
    def _adjust_stench(self,wx:int,wy:int,delta:int):
        for d in Dir:
            ax,ay=wx+d.dx, wy+d.dy
            if 1<=ax<=4 and 1<=ay<=4:
                self.tile_state[ay][ax]['stench']+=delta
                if self.tile_state[ay][ax]['stench']<0:
                    self.tile_state[ay][ax]['stench']=0

    def _adjust_breeze(self,px:int,py:int,delta:int):
        for d in Dir:
            ax,ay=px+d.dx, py+d.dy
            if 1<=ax<=4 and 1<=ay<=4:
                self.tile_state[ay][ax]['breeze']+=delta
                if self.tile_state[ay][ax]['breeze']<0:
                    self.tile_state[ay][ax]['breeze']=0

    # 호환용 별칭 (통합 전 코드에서서 world.gold 사용)
    @property
    def gold(self): return self.gold_xy