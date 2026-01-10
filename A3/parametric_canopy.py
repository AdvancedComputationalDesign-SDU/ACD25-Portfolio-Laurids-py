"""
-------------Assignment 3: Parametric Structural Canopy-------------

Author: Laurids Gerner Ejersbo

Description:
This script generates a structural canopy using Python within GH. The script is heavily commented to
ensure full understanding of every line 
"""

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
# CONVERT SLIDERS TO INTEGERS
# ---------------------------------------------------------------------------
divU = int(divU)
divV = int(divV)
rec_depth = int(rec_depth)
n_branches = int(n_branches)

use_quad = bool(use_quad) # Ensure use_quad is boolean

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
            P[i][j] = rs.EvaluateSurface(surface_id, u, v) # Evaluates surface points at UV-locations - outputs 3D point (x,y,z)
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

def two_center_support_roots(surface_id): # Function to create support bases for branching structure
    du = rs.SurfaceDomain(surface_id, 0) # U-domain of base-surface (u_min, u_max)
    dv = rs.SurfaceDomain(surface_id, 1) # V-domain of base-surface (v_min, v_max)

    UVs = [(0.5, 0.3), (0.5, 0.8)] # Normalized location of support bases

    pts=[] # Creation of empty list
    for uN,vN in UVs:
        u = du[0] + uN*(du[1]-du[0]) # Conversion of normalized U-space to Rhino U-space
        v = dv[0] + vN*(dv[1]-dv[0]) # Conversion of normalized V-space to Rhino V-space
        pts.append(rs.EvaluateSurface(surface_id,u,v)) # Evaluates surface points at UV-locations - outputs 3D points (x,y,z)
    return pts

def generate_supports(roots, depth, length, reduction, branches, seed, canopy_surf): # Function to create branching structure
    seed_everything(seed) # Ensures reproducible randomness
    supports=[] # Creation of empty list
    branches=int(branches) # Ensures GH enteprets "branches" as an integer

    edge_curves = rs.DuplicateEdgeCurves(canopy_surf) # Retrieves surface edges
    boundary_curve = rs.JoinCurves(edge_curves, True)[0] # Joins edges into one closed curve

    pts = rs.CurvePoints(boundary_curve) # Retrieves curve points
    pts_xy = [(pt[0], pt[1], 0) for pt in pts] # Creates a new list of points where Z is forced to 0
    boundary_curve_flat = rs.AddPolyline(pts_xy + [pts_xy[0]])  # Create closed polyline
    rs.DeleteObject(boundary_curve) # Removes original curve

    def grow(pt,d,L): # Recursive growth function
        if d<=0: return # Stops growth if recursion depth is less than or equal to zero
        for _ in range(branches):
            cp = rs.SurfaceClosestPoint(canopy_surf,pt) # UV parameters of closest point on canopy
            tgt = rs.EvaluateSurface(canopy_surf,cp[0],cp[1]) # 3D coordinate of cp
            base_dir = rs.VectorUnitize(rs.VectorCreate(tgt,pt)) # Normalized vector pointing toward the canopy
            jitter = (random.uniform(-0.3,0.3),random.uniform(-0.3,0.3),random.uniform(0,0.3))
            direction = rs.VectorUnitize(rs.VectorAdd(base_dir,jitter))
            end = rs.PointAdd(pt, rs.VectorScale(direction,L)) # Adds end-point

                        # Convert branch endpoint to XY
            end_xy = (end[0], end[1], 0)

            # Skip this branch if outside the canopy footprint
            if not rs.PointInPlanarClosedCurve(end_xy, boundary_curve_flat):
                continue  # do not create branch

            test_line = rs.AddLine(pt,end) # Temporary line to check for surface intersection
            hit = rs.CurveSurfaceIntersection(test_line, canopy_surf) # Check for intersection
            rs.DeleteObject(test_line) # Deletes temporary line
            if hit:
                end = hit[0][1] # 3D intersection point
                supports.append(rs.AddLine(pt,end)) # Adds line from i'th "pt" to "end"
                continue # Stops further recursions

            line = rs.AddLine(pt,end) # Continues growth of branches if line doesn't intersect canopy
            supports.append(line)
            grow(end,d-1,L*reduction) # Creation of new branches with length shrinkage and deduction in depth

    for pt in roots:
        grow((pt[0],pt[1],0), depth, length) # Starts a support at ground-projected root (x,y,0) with initial depth & length

    return supports

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

roots = two_center_support_roots(surf) # Base positions for branching strucutre
supports = generate_supports(roots, rec_depth, br_length, len_reduct, n_branches, seed, surf) # Creates branching support lines starting from base positions (roots)

# Output
out_surface = surf
out_tessellation = mesh
out_supports = supports