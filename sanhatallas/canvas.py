from sys import exit, path
from pathlib import Path

import pygame
from pygame.locals import *

from geometry import XY
from sketch import Line, Divider, HookLine, LineGroup

path.append(str(Path(__file__).parents[1]))
#print(path)
from hantatallas.hack import render, lookup

DIMENSIONS = (1000, 1000)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GREEN = (0, 255, 0)
CYAN = (0, 128, 255)
BLUE = (0, 0, 255)
PINK = (255, 64, 128)
WIDTH = 8

lines = []
progress = None
mode = Line

pygame.init()
display = pygame.display.set_mode(DIMENSIONS)
clock = pygame.time.Clock()

while True:
	for event in pygame.event.get():
		if event.type == QUIT:
			pygame.quit()
			exit()
		elif event.type == MOUSEBUTTONUP:
			if progress is None:
				progress = XY(*pygame.mouse.get_pos())
			else:
				new = XY(*pygame.mouse.get_pos())
				lines.append(mode(progress, new, tolerance=10))
				progress = None
		elif event.type == KEYDOWN:
			if event.key == K_RETURN:
				s = str(LineGroup(lines).parse())
				print(s)
				render(s)
				lookup(s)
			elif event.key == K_BACKSPACE:
				if progress: progress = None
				else: lines.pop()
			elif event.key == K_DELETE:
				lines = []
			elif event.key == K_ESCAPE:
				pygame.quit()
				exit()
			elif event.key == K_1:
				mode = Line
			elif event.key == K_2:
				mode = Divider
			elif event.key == K_3:
				mode = HookLine
	
	display.fill(BLACK)
	for line in lines:
		if isinstance(line, Divider):
			color = BLUE
		elif isinstance(line, HookLine):
			color = PINK
		else:
			color = WHITE
		pygame.draw.line(display, color, line.head, line.tail, WIDTH)
	if progress is not None:
		if mode == Divider:
			color = CYAN
		elif mode == HookLine:
			color = PINK
		else:
			color = GREEN
		pygame.draw.line(display, color, progress, pygame.mouse.get_pos(), WIDTH)
	
	pygame.display.update()
	clock.tick(60)
