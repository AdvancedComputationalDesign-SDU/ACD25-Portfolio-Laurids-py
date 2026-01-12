# ---------------------------------------------------------------------------
# IMPORTS
# ---------------------------------------------------------------------------
#r: numpy
import numpy as np
import rhinoscriptsyntax as rs
import random
import math
import Rhino

# ---------------------------------------------------------------------------
# ENSURE base_surface IS A RHINO SURFACE
# ---------------------------------------------------------------------------
# Grasshopper may pass a GH_Surface wrapper or a GUID instead of a pure Rhino surface (Rhino.Geometry.Surface)
try:
    # Try to access Geometry property (unwrap GH_Surface)
    base_surface = getattr(base_surface, "Geometry", base_surface)

    # Explanation for above: If base_surface has an attribute called Geometry, use that. Otherwise, keep base_surface as it is

except:
    pass # If anything goes wrong above (for example, base_surface is None), the script does nothing

# If input is still a GUID, coerce it to Rhino surface
try:
    import System # Imports the .NET System namespace, which is required to recognize GUID types
    if isinstance(base_surface, System.Guid): # Is base_surface a GUID (just an ID reference)?
        base_surface = rs.coercesurface(base_surface) # This converts the GUID into an actual Rhino.Geometry.Surface
except:
    pass # If anything fails, the script continues safely

# Final type check
import Rhino
if not isinstance(base_surface, Rhino.Geometry.Surface): # Essential question: after all conversions, is base_surface actually a Rhino surface?
    raise TypeError(f"Input base_surface is not a valid Rhino surface. Got {type(base_surface)}")


# ---------------------------------------------------------------------------
# CONVERT SLIDERS TO INTEGERS
# ---------------------------------------------------------------------------
divU = int(divU)
divV = int(divV)
use_quad = bool(use_quad) # Ensure use_quad is boolean (Grasshopper may pass 0/1 or True/False)

# ---------------------------------------------------------------------------
# HELPER FUNCTIONS
# ---------------------------------------------------------------------------
def seed_everything(seed): # Function to ensure reproducible randomness
    if seed is not None:
        random.seed(seed)

def uv_grid(divU, divV): # Initial grid function
    us = np.linspace(0, 1, divU)
    vs = np.linspace(0, 1, divV)
    return np.meshgrid(us, vs, indexing='xy')

def heightmap(U, V, amplitude, frequency, phase): # Heightmap function 
    wave = np.sin(2 * math.pi * frequency * (U + V) + phase) # Sine wave pattern on surface
    cx, cy = 0.5, 0.5 # Central coordinate of grid
    dist = np.sqrt((U-cx)**2 + (V-cy)**2) # Distance from i'th point to central coordinate of grid
    bump = np.exp(-5*dist**2) # Surface bump depending on i'th points proximity to central coordinate of grid
    return amplitude * (0.6*wave + 0.4*bump) # Scaling of the influences

def sample_point_grid_from_surface(surface_id, U, V): # Sample function - used to map normalized grid into the real surface domain
    du = rs.SurfaceDomain(surface_id, 0) # U-domain of base-surface (u_min, u_max)
    dv = rs.SurfaceDomain(surface_id, 1) # V-domain of base-surface (v_min, v_max)
    rows, cols = U.shape # No. of rows and columns generated based on divU and divV
    P = [[None for _ in range(cols)] for __ in range(rows)] # cols-lists of row-components - storage of surface points
    for i in range(rows):
        for j in range(cols):
            u = du[0] + U[i,j]*(du[1]-du[0]) # Conversion of normalized U-space to Rhino U-space
            v = dv[0] + V[i,j]*(dv[1]-dv[0]) # Conversion of normalized V-space to Rhino V-space
            P[i][j] = rs.EvaluateSurface(surface_id, u, v) # Evaluates surface points at UV-locations - outputs 3D points (x,y,z)
    return P

def manipulate_points_along_normals(point_grid, H, surface_id, U, V): # Function to offset points along normals by heightmap 
    du = rs.SurfaceDomain(surface_id, 0) # U-domain of base-surface (u_min, u_max)
    dv = rs.SurfaceDomain(surface_id, 1) # V-domain of base-surface (v_min, v_max)
    rows, cols = H.shape # No. of rows and columns generated based on heightmap-function
    R = [[None for _ in range(cols)] for __ in range(rows)] # cols-lists of row-components - storage for displaced points
    for i in range(rows):
        for j in range(cols):
            p = point_grid[i][j] # Point on surface before displacement
            u = du[0] + U[i,j]*(du[1]-du[0]) # U-domain of base-surface (u_min, u_max)
            v = dv[0] + V[i,j]*(dv[1]-dv[0]) # V-domain of base-surface (v_min, v_max)
            n = rs.SurfaceNormal(surface_id,(u,v)) # 3D vector perpendicular to the surface
            if not n: n=(0,0,1) # Safety fallback - if surface normal cannot be computed, the z-axis is used
            n = rs.VectorUnitize(n) # Normal vector is unitized so scaling w/ heightmap is controlled
            R[i][j] = rs.PointAdd(p, rs.VectorScale(n, H[i,j])) # Displaces point in normal-vector direction by heightmap
    return R

def lift_point_grid(point_grid, lift): # Function to move point grid in vertical direction by fixed "lift"-value
    return [[(p[0],p[1],p[2]+lift) for p in row] for row in point_grid]

def surface_from_point_grid(point_grid): # Function to create surface
    rows=len(point_grid) # No. of rows of points - corresponds to divU
    cols=len(point_grid[0]) # No. of points in each row - corresponds to divV
    pts=[point_grid[i][j] for i in range(rows) for j in range(cols)] # Flattens 2D grid "point_grid" into one list of points
    return rs.AddSrfPtGrid((rows,cols), pts)

# ---------------------------------------------------------------------------
# MESH CREATION: triangle and quad options
# ---------------------------------------------------------------------------
def mesh_from_grid_tri(point_grid): # Function to create triangular faces from grid
    rows=len(point_grid) # No. of rows of points - corresponds to divU
    cols=len(point_grid[0]) # No. of points in each row - corresponds to divV
    mesh=Rhino.Geometry.Mesh() # Creation of empty mesh
    for i in range(rows):
        for j in range(cols):
            mesh.Vertices.Add(point_grid[i][j][0], point_grid[i][j][1], point_grid[i][j][2]) # Flattens every point in the grid as a mesh vertex
    for i in range(rows-1):
        for j in range(cols-1): # Range is limited to (rows-1) and (cols-1) respectively to stay within domain (we use i+1 and j+1 below)
            a=i*cols+j  
            b=i*cols+j+1
            c=(i+1)*cols+j+1
            d=(i+1)*cols+j
            # Above, the indices of the four corners of the i'th 2D grid is converted into  1D vertex indices
            mesh.Faces.AddFace(a,b,c) # Creation of first of two triangular-faces from four vertices
            mesh.Faces.AddFace(a,c,d) # Creation of last of two triangular-faces from four vertices
    mesh.Normals.ComputeNormals() # Creation of normals
    mesh.Compact() # Removes redundancies
    return mesh

def mesh_from_grid_quad(point_grid): # Function to create rectangular faces from grid
    rows=len(point_grid) # No. of rows of points - corresponds to divU
    cols=len(point_grid[0]) # No. of points in each row - corresponds to divV
    mesh=Rhino.Geometry.Mesh() # Creation of empty mesh
    for i in range(rows):
        for j in range(cols):
            mesh.Vertices.Add(point_grid[i][j][0], point_grid[i][j][1], point_grid[i][j][2]) # Flattens every point in the grid as a mesh vertex
    for i in range(rows-1):
        for j in range(cols-1):
            a=i*cols+j
            b=i*cols+j+1
            c=(i+1)*cols+j+1
            d=(i+1)*cols+j
            # See explanatory note from tri-grid
            mesh.Faces.AddFace(a,b,c,d) # Creation of faces
    mesh.Normals.ComputeNormals() # Creation of normals
    mesh.Compact() # Removes redundancies
    return mesh

# ---------------------------------------------------------------------------
# EXECUTION
# ---------------------------------------------------------------------------
seed_everything(seed) # Ensures reproducible randomness
U,V = uv_grid(divU,divV) # Creates two 2D grids (U and V) of normalized UV coordinates from 0..1
H = heightmap(U,V,amplitude,frequency,phase) # Creates displacement grid
P0 = sample_point_grid_from_surface(base_surface,U,V) # Converts normalized UV grids into actual 3D points on surface
P_def = manipulate_points_along_normals(P0,H,base_surface,U,V) # Moves each surface point along the surface normal vector by height H[i,j]
P_def_lifted = lift_point_grid(P_def,10) # Adds +10 to the Z-coordinate of every point

surf = surface_from_point_grid(P_def_lifted) # Rebuilds a NURBS surface from lifted point grid

# Choose quad or triangle mesh based on use_quad input
if use_quad:
    mesh = mesh_from_grid_quad(P_def_lifted)
else:
    mesh = mesh_from_grid_tri(P_def_lifted)

# Output
out_surface = surf
out_tessellation = mesh
out_heightmap = H # new output
out_Ugrid = U  # new output
out_Vgrid = V  # new output