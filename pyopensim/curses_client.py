import curses
import math
import time
from typing import List, Tuple

from .client import OpenSimClient
from .actions import AgentActions

class CursesInterface:
    """Small curses interface for OpenSimClient."""

    def __init__(self, client: OpenSimClient) -> None:
        self.client = client
        self.actions = AgentActions(client)
        self.log: List[str] = []

    # -- helpers -----------------------------------------------------
    def add_log(self, msg: str) -> None:
        self.log.append(msg)
        if len(self.log) > 100:
            self.log.pop(0)

    def draw_logs(self, win) -> None:
        h, w = win.getmaxyx()
        start = max(0, len(self.log) - (h - 2))
        win.erase()
        win.box()
        for i, line in enumerate(self.log[start:], 1):
            win.addnstr(i, 1, line, w-2)
        win.refresh()

    def draw_objects(self, win) -> None:
        h, w = win.getmaxyx()
        win.erase()
        win.box()
        objs = list(self.client.scene.objects.items())
        for idx, (oid, state) in enumerate(objs[: h - 2]):
            pos = state.position
            dist = math.sqrt(pos[0]**2 + pos[1]**2 + pos[2]**2)
            text = f"{oid[:8]} {pos[0]:.1f} {pos[1]:.1f} {pos[2]:.1f} d={dist:.1f}"
            win.addnstr(idx + 1, 1, text, w-2)
        win.refresh()

    # -- main loop ---------------------------------------------------
    def run(self, stdscr) -> None:
        curses.curs_set(0)
        stdscr.nodelay(True)
        h, w = stdscr.getmaxyx()
        obj_win = curses.newwin(h//2, w, 0, 0)
        log_win = curses.newwin(h - h//2, w, h//2, 0)
        self.add_log("Press q to quit. WASD move, e/c fly, t touch")
        last_event = 0
        while True:
            for ev in self.client.event_log[last_event:]:
                etype = ev.get("event", "?")
                self.add_log(str(etype))
            last_event = len(self.client.event_log)
            key = stdscr.getch()
            if key != -1:
                if key in (ord('q'), ord('Q')):
                    break
                elif key in (ord('w'), ord('W')):
                    self.actions.walk_forward()
                elif key in (ord('s'), ord('S')):
                    self.actions.walk_backward()
                elif key in (ord('a'), ord('A')):
                    self.actions.strafe_left()
                elif key in (ord('d'), ord('D')):
                    self.actions.strafe_right()
                elif key in (ord('e'), ord('E')):
                    self.actions.fly_up()
                elif key in (ord('c'), ord('C')):
                    self.actions.fly_down()
                elif key in (ord('t'), ord('T')):
                    oid = min(self.client.scene.objects,
                               key=lambda o: math.dist(self.client.scene.objects[o].position, (0,0,0)),
                               default=None)
                    if oid:
                        self.actions.touch(oid)
                        self.add_log(f"Touched {oid}")
            self.draw_objects(obj_win)
            self.draw_logs(log_win)
            time.sleep(0.1)


def run_curses_client(login_uri: str, first: str, last: str, password: str) -> None:
    client = OpenSimClient(login_uri, '', password, first, last)
    if not client.login():
        print("Login failed")
        return
    try:
        curses.wrapper(CursesInterface(client).run)
    finally:
        client.disconnect()
