import pygame
import random
import time
import json

#GRID_SIZE = (24, 24)

# Program state variables
# grid_ready is true if the grid is able to be displayed
grid_ready = False
wfc_state = ""
iter_count = 0
attempts = 0
attempts_sum = 0

# These variables described in wfc()
max_trials = 0
num_trials = 0
avg_testing = False

# Some customizable variables
wrap = False
delay = 0
tile_size = (32, 32)

# Timer
start_time = 0

### TILES ###

# This class handles the display of tiles
class TileSprite(pygame.sprite.Sprite):
    def __init__(self, angle, fname, flip_vert = False, flip_horz = False) -> None:
        super().__init__()
        self.surf = pygame.image.load(fname).convert_alpha()
        #self.rect = self.surf.get_rect(center=(400, 400))
        #self.angle = 0
        self.surf = pygame.transform.rotate(self.surf, angle)
        self.rect = self.surf.get_rect()
        self.surf = pygame.transform.scale(self.surf, tile_size)
        self.surf = pygame.transform.flip(self.surf, flip_horz, flip_vert)

# There are 2 in case I want to change functionality in the future. 
# At the present, the first "Tile" class isn't strictly necessary. 
# IndexedTile is the one that actually gets used,
class Tile:
    def __init__(self, sprite, rules):
        self.sprite = sprite
        self.rules = rules

class IndexedTile(Tile):
    def __init__(self, sprite, idxes):
        super().__init__(sprite, None)
        self.idxes = idxes
##############

# Each tile is represented as an index.
# Use this dict to get actual information on specific tiles.
# This dict is generated later.
idx_to_tile = {}

# 2 dimensional array representing the grid, where each cell is a list of possible states.
# I guess that makes this actually 3-dimensionsal.
# If a tile has only one possible state, it is considered collapsed.
grid = []

#
# The following 4 functions generate transformations of tiles.
#
def get_4_indexed_tile_rotations(sprite, fname, idxes):
    tiles = []

    tiles.append(IndexedTile(sprite(0, fname), idxes))
    idxes = [idxes[3], idxes[0], idxes[1], idxes[2]]
    tiles.append(IndexedTile(sprite(-90, fname), idxes))
    idxes = [idxes[3], idxes[0], idxes[1], idxes[2]]
    tiles.append(IndexedTile(sprite(-180, fname), idxes))
    idxes = [idxes[3], idxes[0], idxes[1], idxes[2]]
    tiles.append(IndexedTile(sprite(-270, fname), idxes))

    return tiles

def get_2_indexed_tile_rotations(sprite, fname, idxes):
    tiles = []

    tiles.append(IndexedTile(sprite(0, fname), idxes))
    idxes = [idxes[3], idxes[0], idxes[1], idxes[2]]
    tiles.append(IndexedTile(sprite(-90, fname), idxes))

    return tiles

def get_tile_vert_flip(sprite, fname, idxes):
    tiles = []

    tiles.append(IndexedTile(sprite(0, fname), idxes))
    idxes = [idxes[2], idxes[1], idxes[0], idxes[3]]
    tiles.append(IndexedTile(sprite(0, fname, True, False), idxes))

    return tiles

def get_tile_horz_flip(sprite, fname, idxes):
    tiles = []

    tiles.append(IndexedTile(sprite(0, fname), idxes))
    idxes = [idxes[0], idxes[3], idxes[2], idxes[1]]
    tiles.append(IndexedTile(sprite(0, fname, False, True), idxes))

    return tiles

### JSON TILE LOADER ###

# This loads information about the tiles from tiles.json
def load_tiles_from_json():
    # Load the json
    tile_json = None
    with open('tiles.json', 'r') as file:
        tile_json = file.read()
    tile_json = json.loads(tile_json)

    # Ensure there are actually tiles
    if not ("tiles" in tile_json) or (len(tile_json["tiles"]) == 0):
        print("\nERROR reading tile json: No tiles.\n")
        return []
    
    tiles = []

    # Loop over the tiles in the json
    for tile in tile_json["tiles"]:
        # Ensure needed values exist.
        if not ("fname" in tile):
            print("\nERROR reading tile json: Tile doesn't contain sprite path.\n")
            return []
        if not ("indexes" in tile) or (len(tile["indexes"]) != 4):
            print("\nERROR reading tile json: Tile doesn't contain 4 indexes.\n")
            return []

        # Generate transformations as specified.
        if "transform" in tile:
            match tile["transform"]:
                # 4 rotations, e.g. elbow-shaped tile.
                case "rot-4":
                    tiles.extend(get_4_indexed_tile_rotations(TileSprite, tile["fname"], tile["indexes"]))
                # 2 rotations, e.g. bar-shaped tile.
                case "rot-2":
                    tiles.extend(get_2_indexed_tile_rotations(TileSprite, tile["fname"], tile["indexes"]))
                # Vertical mirror
                case "flip-vert":
                    tiles.extend(get_tile_vert_flip(TileSprite, tile["fname"], tile["indexes"]))
                # Horizontal mirror
                case "flip-horz":
                    tiles.extend(get_tile_horz_flip(TileSprite, tile["fname"], tile["indexes"]))
                # No transformations
                case _:
                    tiles.append(IndexedTile(TileSprite(0, tile["fname"]), tile["indexes"]))
        # No transformations
        else:
            tiles.append(IndexedTile(TileSprite(0, tile["fname"]), tile["indexes"]))
        
    return tiles
                    



########################

# Generate the grid, and the idx_to_tile dictionary, explained above.
def initialize_grid(tiles):
    for x in range(GRID_SIZE[0]):
        grid.append([])
        for y in range(GRID_SIZE[1]):
            grid[x].append([x for x in range(len(tiles))])
    
    for i in range(len(tiles)):
        idx_to_tile[i] = tiles[i]
    
    global grid_ready
    grid_ready = True
    print("Grid initialized!")


###### THE ALGORITHM ######

# Each direction is represented by an index
# It starts at the top, and goes clockwise
# This returns the opposite of a specified direction
# Alleviates the need for weird math stuff
opposite_dir = {
    0: 2,
    1: 3,
    2: 0,
    3: 1
}

# Get the tile at a position
def tile_at_pos(pos):
    return grid[pos[0]][pos[1]]

# Get a list of all positions of tiles
def get_tile_pos_list():
    positions = []
    for x in range(GRID_SIZE[0]):
        for y in range(GRID_SIZE[1]):
            positions.append((x, y))
    return positions

# How's the algorithm doing.
# "contradiction" is failure
# "collapsed" is success
# "uncertain" is still running
def get_wfc_state():
    tiles = get_tile_pos_list()
    collapsed = True
    for tile in tiles:
        states = len(tile_at_pos(tile))
        if states == 0:
            return "contradiction"
        elif states != 1:
            collapsed = False
    return "collapsed" if collapsed else "uncertain"

# 
def get_tiles_sorted_by_entropy():
    sort = lambda a: len(tile_at_pos(a))
    tiles = [x for x in get_tile_pos_list()]
    tiles.sort(key=sort)
    return tiles

def get_sorted_uncollapsed_tiles():
    return [x for x in get_tiles_sorted_by_entropy() if len(tile_at_pos(x)) >= 2]

# Get the positions neighboring a specified position
# Optionally supports wrapping, where the neighbor to the right of a
# tile on the right edge is a tile on the left edge, for example.
def get_neighbors(pos, wrap):
    neighbors = []

    # Up
    if pos[1] == 0:
        if wrap:
            neighbors.append((pos[0], GRID_SIZE[1] - 1))
        else:
            neighbors.append(None)
    else:
        neighbors.append((pos[0], pos[1] - 1))

    # Right
    if pos[0] == (GRID_SIZE[0] - 1):
        if wrap:
            neighbors.append((0, pos[1]))
        else:
            neighbors.append(None)
    else:
        neighbors.append((pos[0] + 1, pos[1]))

    # Down
    if pos[1] == (GRID_SIZE[1] - 1):
        if wrap:
            neighbors.append((pos[0], 0))
        else:
            neighbors.append(None)
    else:
        neighbors.append((pos[0], pos[1] + 1))

    # Left
    if pos[0] == 0:
        if wrap:
            neighbors.append((GRID_SIZE[0] - 1, pos[1]))
        else:
            neighbors.append(None)
    else:
        neighbors.append((pos[0] - 1, pos[1]))

    return neighbors
    


def propogate(pos):
    # Tiles to be propogated
    stack = [pos]

    while len(stack) > 0:
        tile = stack.pop()
        
        neighbors = get_neighbors(tile, wrap)
        # For each direction
        for idx in range(4):
            # On each side, narrow down possible states.
            possible_states = []

            neighbor = neighbors[idx]
            if neighbor == None:
                continue

            # Tile to propogate to
            propogate_to = tile_at_pos(neighbor)
            # Tile to propogate from
            propogate_from = tile_at_pos(tile)

            # For each possible state in the tile we're propogating from
            #
            # NOTE: Indexes control which tiles can neighbor which other tiles
            # Each tile has one index on each side.
            # So a tile with an index of 1 on the top can only neighbor (in that direction)
            # Tiles with index 1 on the bottom.
            #
            for from_state in propogate_from:
                from_idx = idx_to_tile[from_state].idxes[idx]
                
                # For each possible state in the tile we're propogating to
                for to_state in propogate_to:
                    to_idx = idx_to_tile[to_state].idxes[opposite_dir[idx]]

                    # Only add to the list of possible states if indexes match
                    if from_idx == to_idx:
                        if not (to_state in possible_states):
                           possible_states.append(to_state)
            
            possible_states.sort()

            #print(possible_states)
            #print(propogate_to)
            #print('------')

            # Propogate further, if needed. 
            # Also an extra check for a contradiction
            if possible_states != propogate_to:
                if len(possible_states) == 0:
                    return False
                stack.append(neighbor)
                # Update the tile with the new possible states
                grid[neighbor[0]][neighbor[1]] = possible_states


# Algorithm iteration
def iterate():
    global iter_count
    iter_count += 1
    print(f"\nBeginning WFC Iteration #{iter_count}.\n")

    # Step 1: Collapse random uncollapsed tile
    tiles = get_sorted_uncollapsed_tiles()
    # Tiles with the lowest possible states, but they must be uncollapsed
    low_entropy_tiles = [x for x in tiles if len(tile_at_pos(x)) == len(tile_at_pos(tiles[0]))]
    # Choose random tile
    tile = random.choice(low_entropy_tiles)
    # Choose random state
    tile_val = [random.choice(tile_at_pos(tile))]
    # Collapse the tile
    grid[tile[0]][tile[1]] = tile_val

    # Step 2: Propogate Information to Neighbors, Recursively
    if propogate(tile) == False:
        # Failed
        return False

# The main function of the algorithm.
def wfc():
    # Increment variables
    global attempts
    global attempts_sum
    global num_trials
    attempts += 1
    num_trials += 1
    attempts_sum += attempts
    print(f"\nStarting Algorithm! Attempt #{attempts}")
    
    # Loop until finished.
    global wfc_state
    while True:
        # Get program state
        wfc_state = get_wfc_state()
        match wfc_state:
            # Program success
            case "collapsed":
                print(f"Algorithm Attempt #{attempts} Finished Successfully!")

                #
                # Avgerage testing, if enabled, runs the algorithm a specified number of times
                # and prints the average number of attemps.
                #
                if avg_testing:
                    attempts = 0
                    if num_trials < max_trials:
                        # Do a new trial
                        print(f"Starting Trial #{num_trials}")
                        #time.sleep(1)
                        restart()
                    else:
                        # All trials finished
                        print(str(attempts_sum / max_trials))
                return
            # Program faiure
            case "contradiction":
                print(f"Algorithm Attempt #{attempts} Finished With Contradiction.")
                restart()
                return
        # Also program failure. Without this, the grid erases itself for some reason
        # and then restarts, which takes longer (though it does look kinda cool)
        if iterate() == False:
            print(f"Algorithm Attempt #{attempts} Finished With Contradiction.")
            restart()
            return
        
        # Delay between iterations, if specified
        time.sleep(delay)


# Re-initialize variables and try again
def restart():
    global grid_ready
    grid_ready = False
    global wfc_state
    wfc_state = ""
    global iter_count
    iter_count = 0
    global idx_to_tile
    idx_to_tile = {}
    global grid
    grid = []
    begin_wfc()

# Starts an attempt of the algorithm
def begin_wfc():
    print("Beginning Wave Function Collapse!")

    # Get the tiles to be used, from json
    tiles = load_tiles_from_json()
    if len(tiles) == 0:
        print("Errors loading tile json. Exiting.")
        global wfc_state
        wfc_state = "contradiction"
        return
    
    ######

    # This was used for testing.
    # It added the tiles more manually. I like the json setup better
    # But, I'll leave this here, just in case.
    #tiles.extend(get_indexed_tile_rotations(TileSprite, "tile_t.png", [1, 1, 0, 1]))
    #tiles.extend(get_indexed_tile_rotations(TileSprite, "tile_l.png", [1, 1, 0, 0]))
    
    ######

    initialize_grid(tiles)

    # BEGIN!!
    wfc()


# Only called on the first attempt. Initializes "constants" and starts timer.
def enter(screen_size, p_tile_size, p_wrap, delay_seconds, trial_testing=0):
    global GRID_SIZE
    GRID_SIZE = screen_size

    global tile_size
    tile_size = p_tile_size

    global wrap
    wrap = p_wrap

    global delay
    delay = delay_seconds

    if trial_testing > 0:
        global avg_testing
        avg_testing = True
        global max_trials
        max_trials = trial_testing
    
    # Start the timer
    global start_time
    start_time = time.time()
    
    # Start attempt 1!
    begin_wfc()

    # Print total algorithm run time
    print(f"Program finished in {time.time() - start_time} seconds.")
    