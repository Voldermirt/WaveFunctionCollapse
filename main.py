import pygame
import wfc
import threading
import time

# This is a simple implementation of a "Wave Function Collapse Algorithm," which was invented, 
# as far as I can tell, by Maxim Gumin (https://github.com/mxgmn/WaveFunctionCollapse).
# The idea is taken from quantum physics, though I don't know much about that.
# Essentially, there is a grid (in this implementation) of tiles, 
# and each tile is in a superposition of a number of different states.
# For each iteration of the program, it selects a random tile among those with 
# the least "entropy" (or "uncertainty", basically the number of possible states it can be in).
# It "collapses" that tile into exactly one of its possible states, randomly. 
# It then propogates that information to its neighboring tiles, which may
# update their list of possible states accordingly, 
# based on rules of which tiles can fit together, and then propogate that information further.
# The result is the computer procedurally generating a grid of 
# tiles that all fit together nicely, in a similar manner to how one plays sudoku.
# Rarely, the program runs into a "contradiction," where it finds a tile that has no possible states. 
# If this happens, it automatically restarts and tries again.

# This file mainly just starts the algorithm and displays the progress.
# wfc.py contains the actual algorithm
# And tiles.json contains information about the tiles to be used.

# Save the result as a png
def save_image(screen):
    # Give the file a name according to the current time
    t = time.strftime("%Y-%m-%d_%H-%M-%S")
    pygame.image.save(screen, f"out/WVC_{t}.png")

# Display the actual tiles to the screen
def display_grid(screen):
    
    if wfc.grid_ready:
        for x in range(len(wfc.grid)):
            for y in range(len(wfc.grid[x])):
                tile = wfc.grid[x][y]
                # If the tile is collapsed
                if len(tile) == 1:
                    screen.blit(wfc.idx_to_tile[tile[0]].sprite.surf, (x * tile_size[0], y * tile_size[1]))

    pygame.display.flip()

# The pygame module is used for the display.
pygame.init()

# How many tiles on a side of the grid. This can (and should) be modified, as wanted.
SCREEN_TILE_SIZE = (50, 50)
# The window size, in pixels.
SCREEN_SIZE = (800, 800)

# Display the screen
screen = pygame.display.set_mode(SCREEN_SIZE)

# Calculate how many pixels wide each tile should be
tile_size = (SCREEN_SIZE[0] / SCREEN_TILE_SIZE[0], SCREEN_SIZE[1] / SCREEN_TILE_SIZE[1])

# Start the actual algorithm in a separate thread
wfc_thread = threading.Thread(target=wfc.enter, daemon=True,args=(SCREEN_TILE_SIZE, tile_size, True, 0.0))
wfc_thread.start()

# Save the result to a file?
DO_SCREENSHOTS = True

# Otherwise, it screenshots every frame
taken_screenshot = False

# Main loop
running = True
while running:
    
    # Handle quit request
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
    

    # Display the screen, based on the state of the algorithm.
    if wfc.wfc_state == "collapsed":
        # Take screenshot if algorithm just finished
        if not taken_screenshot and DO_SCREENSHOTS:
            display_grid(screen)
            save_image(screen)
            taken_screenshot = True
        else:
            screen.fill((194, 255, 161))
            display_grid(screen)
    elif wfc.wfc_state == "contradiction":
        screen.fill((140, 31, 47))
        display_grid(screen)
    else:
        screen.fill((255, 255, 255))
        display_grid(screen)


pygame.quit()

