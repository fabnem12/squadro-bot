import numpy as np
from matplotlib import image
from matplotlib import pyplot as plt

def pixelize(img, size):
    """ Fill size*size square tiles with average color."""
    tiles = img.copy()
    h, w = np.shape(tiles)
    for r in range(0, h, size):
        for c in range(0, w, size):
            tiles[r:r+size, c:c+size] = np.mean(tiles[r:r+size, c:c+size])
    return tiles

def zoom(img, size):
    """ return zoomed numeric tiles grid."""
    h, w = np.shape(img)
    result = np.zeros((int(h/size)+1, int(w/size)+1), dtype=np.int)
    for r in range(0, h, size):
        for c in range(0, w, size):
            result[int(r/size), int(c/size)] = np.min(img[r:r+size, c:c+size])
            return result


def main(img):
    # Prepare a figure of 2x2 subplots
    fig1, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2)

    # display original image
    ax1.set_title('original')
    ax1.imshow(img)

    # Computes and display redness
    red = img[:, :, 0] / 255.
    green = img[:, :, 1] / 255.
    blue = img[:, :, 2] / 255.
    redness = ((red - ((green + 2*blue)/3.)) + 1.) / 2.
    ax2.set_title('terrain')
    ax2.imshow(redness, cmap='gist_earth')

    # Computes and display pixelized redness map
    tile_size = 16
    tiles = pixelize(redness, tile_size)
    ax3.set_title('tiles')
    ax3.imshow(tiles, cmap='Reds')

    # Computes and display pixelized threshold map
    threshold = 0.5
    grid = tiles.copy()
    grid[grid > threshold] = 1.0
    grid[grid <= threshold] = 0.0
    ax4.set_title('grid')
    ax4.imshow(1-grid, cmap='binary')

    # Zoom out binary picture into abstract map
    game_board = zoom(grid, tile_size)
    #print(game_board)
    #print(game_board == 1)

    # Save numeric game board as text grid
    text_grid = game_board.astype('<U1')
    text_grid[game_board == 1] = '.'
    text_grid[game_board == 0] = '#'
    #print(text_grid.shape)
    #print(text_grid)

    np.savetxt('./game.txt',
               text_grid,
               delimiter=',',
               fmt='%s'
               )

   # Display our 4 plots
   return plt
