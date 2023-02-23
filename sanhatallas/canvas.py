from sys import exit, path
from pathlib import Path

import pygame
from pygame.locals import *

from geometry import XY
from sketch import Line, LineGroup

path.append(str(Path(__file__).parents[1]))
#print(path)
from hantatallas.hack import render, lookup

DIMENSIONS = (1000, 1000)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GREEN = (0, 255, 0)
WIDTH = 8

lines = []
progress = None

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
				lines.append(Line(progress, new))
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
	
	display.fill(BLACK)
	for line in lines:
		pygame.draw.line(display, WHITE, line.head, line.tail, WIDTH)
	if progress is not None:
		pygame.draw.line(display, GREEN, progress, pygame.mouse.get_pos(), WIDTH)
	
	pygame.display.update()
	clock.tick(60)
