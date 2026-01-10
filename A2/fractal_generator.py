"""
-------------Assignment 2: Fractal Generator-------------
Author: Laurids Gerner Ejersbo
Description:
This script generates fractal patterns using recursive functions and geometric transformations.
"""

# --- IMPORTS ---
import math
import matplotlib.pyplot as plt
from shapely.geometry import LineString, Polygon, Point
import random

# --- GLOBALS ---
line_list = []                      # Stores recursive line segments

# --- PARAMETERS ---
random.seed(100)                    # Int, can be changed to obtain a different reproducible fractal
start_point = (0, 0)                # Tuple, initial point (x,y) of fractal
initial_angle = 90                  # Float, initial angle of first line in global system
initial_length = 30                 # Float, initial length of first line in global system    
recursion_depth = 0                 # Int, first level of recursion
max_recursion_depth = 10            # Int, total recursions for the fractal
angle_change = 30                   # Float, angle of branching
length_scaling_factor = 0.7         # Float, each branch is 70% the length of the previous segment
attractor_point = (100,100)         # Tuple, attractor point (x,y)


# --- REGION OF DOMAIN AND OBSTACLES ---

# Allowed region (rectangle)
allowed_region = Polygon([(-50,0), (100,0), (100,100), (-50,100)])    

# Circular obstacle with center at (100,100) and radius 5
circle_obstacle1 = Point(80, 80).buffer(10)                       # Shapely Polygon representing a circle
circle_obstacle2 = Point(-20, 80).buffer(5)                       # Shapely Polygon representing a circle
obstacles = [circle_obstacle1,circle_obstacle2]                   # Possibility to add multiple obstacles

# Functions to be integrated in recursive fractal function
def is_within_region(point):
    """Check if a point is inside the allowed region"""
    return allowed_region.contains(Point(point))                # Branch is discarded if point is outside boundary

def intersects_obstacles(line):
    """Check if a line intersects any obstacle"""
    return any(line.intersects(obs) for obs in obstacles)       # If branch intersects w/ obstacle, it is neither drawn or continued

def intersects_self(line):
    """Check if a line crosses any existing line in the fractal"""
    # return any(line.crosses(existing_line) for existing_line, _ in line_list) # Branch is discarded if a new line crosses a previous one


# --- RECURSIVE FRACTAL FUNCTION ---

def generate_fractal(start_point, angle, length, depth, max_depth, angle_change, length_scaling_factor): 
    """
    Recursive function to generate fractal patterns.
    Parameters are inserted above
    """
    if depth > max_depth:                                                                           # Recursion is stopped when depth exceeds max_depth
        return

    # --- Random variation ---
    angle_variation = angle + random.uniform(-5, 5)                                                 # Adds controlled randomness to change of angle
    length_variation = length * (length_scaling_factor + random.uniform(-0.05, 0.05))               # Adds controlled randomness to change of length

    # --- Calculation of end point of line segment ---
    end_x = start_point[0] + length_variation * math.cos(math.radians(angle_variation))             # x-coord of line segment
    end_y = start_point[1] + length_variation * math.sin(math.radians(angle_variation))             # y-coord of line segment
    end_point = (end_x, end_y)                                                                      # End point of line segment

     # --- Geometric influence: Attractor ---
    dx = attractor_point[0] - end_point[0]                                              # x-component of vector from end-point to attractor point
    dy = attractor_point[1] - end_point[1]                                              # y-component of vector from end-point to attractor point
    angle_to_attractor = math.degrees(math.atan2(dy, dx))                               # Angle of vector from end-point of line to attractor point
    influence_strength = 0.1                                                            # Size of effect of attractor point
    angle_variation += influence_strength * (angle_to_attractor - angle_variation)      # Angle variation w/ effect of attractor point

    # --- Create line segment ---
    line = LineString([start_point, end_point])                                         # Converts start and end points into Shapely line object            
    
    # --- Rule checks ---
    if not is_within_region(end_point):
        return                                                                          # Skip branch outside allowed region
    if intersects_obstacles(line):
        return                                                                          # Skip branch that hits obstacle
    if intersects_self(line):
        return                                                                          # Skip branch that intersects existing branches
    line_list.append((line, depth))                                                     # Appends line to line_list

    # --- Recursive calls for branches ---
    next_depth = depth + 1
    generate_fractal(end_point, angle_variation + angle_change, length_variation, next_depth, max_depth, angle_change, length_scaling_factor)    
    generate_fractal(end_point, angle_variation - angle_change, length_variation, next_depth, max_depth, angle_change, length_scaling_factor)    
    # Note: Above, using 'angle_variation ± angle_change' splits branches. The "next_depth" increments the depth by 1 to track recursion level


# --- MAIN EXECUTION ---
if __name__ == "__main__":
    line_list.clear()                                                                       # Erases previously defined lines, if script runs multiple times

    # Generate fractal
    generate_fractal(start_point, initial_angle, initial_length, recursion_depth, max_recursion_depth, angle_change, length_scaling_factor)

# --- VISUALIZATION ---

    # Plot of fractal lines
    fig, ax = plt.subplots()
    fig.patch.set_facecolor('black')                                                        # Figure background
    ax.set_facecolor('black')                                                               # Plotting area background
    for line, depth in line_list:
        x, y = line.xy                                                                      # Iterates over all lines and plots using Matplotlib
        color_mod = plt.cm.autumn(depth / max_recursion_depth)                              # Color depends on recursion depth
        linewidth_mod = max(1.0, 3.0 - depth*0.5)                                           # Linewidth depends on recursion depth
        ax.plot(x, y, color=color_mod, linewidth=linewidth_mod)

    # Plot of domain, obstacle and attractor point
    x_dom, y_dom = allowed_region.exterior.xy                                               # Outer boundary of allowed region
    ax.plot(x_dom, y_dom, color='black', linewidth=1, linestyle='-')                        # Rendering of boundary

    for obs in obstacles:
        x_obs, y_obs = obs.exterior.xy                                                      # Outer boundary of obstacle(s)
        ax.fill(x_obs, y_obs, color='green', alpha=0.3)                                     # Rendering of obstacle

    ax.plot(attractor_point[0], attractor_point[1], 'bo', markersize=6)                     # Rendering of attractor point

    ax.set_aspect('equal')                                                                  # Prevents distortion
    plt.axis('off')                                                                         # Axes turned off
    plt.show()                                                                              # Rendering of image    

    fig.savefig('images/fractal_var4.png', dpi=300, bbox_inches='tight')                    # Save of figure