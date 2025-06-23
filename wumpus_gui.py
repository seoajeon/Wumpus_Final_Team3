import tkinter as tk
from tkinter import messagebox
from setting import World
from agent import Agent
import os

SUCCESS = [ 1111, 900, 17,  88,  101, 402, 600, 1000]
SEED_FILE = "current_seed.txt"








def get_next_seed():
    if os.path.exists(SEED_FILE):
        with open(SEED_FILE, "r") as f:
            index = int(f.read().strip())
    else:
        index = 0

    next_index = (index + 1) % len(SUCCESS)
    with open(SEED_FILE, "w") as f:
        f.write(str(next_index))

    return SUCCESS[index]


CHOSEN_SEED = get_next_seed()


class WumpusWorldGUI:
    def __init__(self, root):
        self.root = root
        self.root.title(f"Wumpus World GUI - Seed {CHOSEN_SEED}")

        self.world = World(seed=CHOSEN_SEED)
        self.agent = Agent(self.world)
        self.deaths = 0

        self.grid_frame = tk.Frame(self.root)
        self.grid_frame.pack()

        self.labels = [
            [tk.Label(self.grid_frame, width=4, height=2, borderwidth=2,
                      relief="solid", font=("Arial", 20), anchor="center")
             for _ in range(4)] for _ in range(4)
        ]

        for y in range(4):
            for x in range(4):
                self.labels[y][x].grid(row=y, column=x)

        self.info = tk.Label(self.root, text="Step: 0 | Score: 0 | Arrows: 3", font=("Arial", 12))
        self.info.pack(pady=5)

        self.step_count = 0
        self.update_display()
        self.root.after(500, self.step)

    def update_display(self):
        for y in range(4):
            for x in range(4):
                tx, ty = x + 1, 4 - y
                label = self.labels[y][x]

                emoji = ""
                if (tx, ty) == (self.agent.x, self.agent.y):
                    emoji = {
                        "E": "â¡ï¸", "W": "â¬ï¸", "N": "â¬ï¸", "S": "â¬ï¸"
                    }[self.agent.dir.name]
                elif (tx, ty) == self.world.gold_xy and not self.agent.has_gold:
                    emoji = "ð§"
                elif (tx, ty) in self.world.wumpi:
                    emoji = "ð¹"
                elif (tx, ty) in self.world.pits:
                    emoji = "ð³ï¸"

                label.config(text=emoji)

        self.info.config(
            text=f"Step: {self.step_count} | Score: {self.agent.performance} | Arrows: {self.agent.arrows}"
        )

    def step(self):
        self.step_count += 1
        alive = self.agent.step(self.step_count)
        self.update_display()

        if not alive:
            self.deaths += 1
            messagebox.showwarning("ì¬ë§", f"ìì´ì í¸ê° ì£½ììµëë¤. (ì´ {self.deaths}í)")
            self.agent.reset_position()
            self.update_display()

        if self.agent.has_gold and (self.agent.x, self.agent.y) == (1, 1):
            self.agent.print_history()
            messagebox.showinfo("ì±ê³µ", "ê¸ íë í íì¶ ì±ê³µ!")
            return

        if self.step_count >= 120:
            self.agent.print_history()
            messagebox.showinfo("ì¤í¨", "ì¤í ì í ëë¬. ì¢ë£í©ëë¤.")
            return

        self.root.after(500, self.step)


if __name__ == "__main__":
    root = tk.Tk()
    app = WumpusWorldGUI(root)
    root.mainloop()
