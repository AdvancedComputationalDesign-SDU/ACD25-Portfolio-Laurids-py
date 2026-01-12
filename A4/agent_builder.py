"""
Assignment 4: Agent-Based Model for Surface Panelization
Author: Laurids Ejersbo

Description:
Defines the core Agent class and factory methods for constructing an
agent-based system. This version ensures correct surface handling,
full surface coverage for agents, and internal storage of heightmap/UV grids.
"""

# --------------------------------------------------------------------------
# Imports
# --------------------------------------------------------------------------
import rhinoscriptsyntax as rs
import random
import numpy as np
import Grasshopper
import Rhino

# --------------------------------------------------------------------------
# Utility function for reproducibility
# --------------------------------------------------------------------------
def seed_everything(seed):
    """Set random seeds for reproducibility."""
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)

seed_everything(42)  # Ensures reproducible randomness

# --------------------------------------------------------------------------
# Core Agent Class
# --------------------------------------------------------------------------
class Agent:
    """Represents a single agent on a surface."""
    def __init__(self, id, position, velocity, surface, slope_weight=1.0, curvature_weight=1.0): # Initializes an agent
        self.id = id
        self.position = position
        self.velocity = velocity
        self.surface = surface
        self.age = 0
        self.history = [position]
        self.slope_weight = slope_weight
        self.curvature_weight = curvature_weight

        # UV coordinates in [0,1] for heightmap indexing
        self.uv = (0, 0)

        # Heightmap and grid references (assigned externally)
        self.heightmap = None
        self.U_grid = None
        self.V_grid = None

    def sense(self, heightmap, U_grid, V_grid): # Computes environmental signals at the agent’s location
        """Sample slope and curvature signals at the agent's current position."""
        u_vals = U_grid[0, :] # Extracts 1D arrays of U coordinates from the structured grid
        v_vals = V_grid[:, 0] # Extracts 1D array of V coordinates from the structured grid

        # Find nearest index in grid
        u_idx = np.argmin(np.abs(u_vals - self.uv[0]))
        v_idx = np.argmin(np.abs(v_vals - self.uv[1]))

        # Compute slope using finite differences
        dH_du = np.gradient(heightmap, axis=1) # Finite-difference approximation of height change in U
        dH_dv = np.gradient(heightmap, axis=0) # # Finite-difference approximation of height change in V
        slope = np.sqrt(dH_du[v_idx, u_idx]**2 + dH_dv[v_idx, u_idx]**2) # Gradient magnitude expressed as scalar slope value.
        self.slope_signal = slope * self.slope_weight

        # Compute curvature on the surface
        uv = rs.SurfaceClosestPoint(self.surface, self.position) # Computes the surface UV corresponding to the agent’s 3D position
        if uv: # Ensures a valid UV is found
            curvature = rs.SurfaceCurvature(self.surface, uv) # Evaluation of curvature
            if curvature:
                k1 = curvature[2] # Principal curvature k1
                k2 = curvature[3] # # Principal curvature k2
                k = k1 + k2 # Total principal curvature
            else:
                k = 0

        else:
            k = 0 # Fallback if UV lookup fails
        self.curvature_signal = k * self.curvature_weight

    def decide(self, du=0.01, dv=0.01): # Determines motion direction from sensed data
        """Update velocity based on sensed slope and curvature."""
        u, v = self.uv # Current UV coordinates
        pt_center = rs.EvaluateSurface(self.surface, u, v) # Agent’s current 3D position
        pt_u = rs.EvaluateSurface(self.surface, u + du, v) # Nearby samples along U direction
        pt_v = rs.EvaluateSurface(self.surface, u, v + dv) # Nearby samples along V directions

        slope_vec = [(pt_u[i] - pt_center[i]) * (-1) for i in range(3)] # # Approximates downhill direction on the surface in u-direction
        slope_vec_v = [(pt_v[i] - pt_center[i]) * (-1) for i in range(3)] # Approximates downhill direction on the surface in v-direction
        slope_vec_combined = [(slope_vec[i] + slope_vec_v[i]) * self.slope_weight for i in range(3)] # Combines slopes in u and v-direction and applies weighting
        curvature_vec = [-slope_vec_combined[i] * self.curvature_signal for i in range(3)] 
        self.velocity = [slope_vec_combined[i] + curvature_vec[i] for i in range(3)] # Final velocity vector

    def move(self, du=0.01, dv=0.01): # Advances the agent in UV space
        """Update agent position constrained to surface."""
        u, v = self.uv # Current UV coordinates
        u_new = max(0.0, min(1.0, u + self.velocity[0] * du)) # Updates U-coordinates with velocity influence and boundary clamping
        v_new = max(0.0, min(1.0, v + self.velocity[1] * dv)) # Updates V-coordinates with velocity influence and boundary clamping
        self.uv = (u_new, v_new)
        self.position = rs.EvaluateSurface(self.surface, self.uv) # Maps UV back into 3D space
        self.history.append(self.position)
        self.age += 1 # Logs trajectory and increments time

    def update(self): # Executes the full cycle  (sense -> decide -> act)
        """Perform one update cycle using internally stored heightmap and grids."""
        self.sense(self.heightmap, self.U_grid, self.V_grid)
        self.decide()
        self.move()

# --------------------------------------------------------------------------
# Factory function: Build agents on surface
# --------------------------------------------------------------------------
def build_agents(num_agents, surface, heightmap, U_grid, V_grid, slope_weight=1.0, curvature_weight=1.0): # Creates and initializes the agent population
    """
    Create a list of agents randomly distributed over the entire surface.
    UVs are correctly mapped from [0,1] to surface domains.
    """
    agents = [] # Empty list to store agents
    num_agents = int(num_agents) # Ensure slider input is integer-type

    for i in range(num_agents):
        # Random normalized UV in [0,1]
        u_norm = random.random()
        v_norm = random.random()

        # Map to actual surface domain
        u_domain = rs.SurfaceDomain(surface, 0) # True surface u-domain
        v_domain = rs.SurfaceDomain(surface, 1) # True surface v-domain
        # Maps normalized UV to surface space
        u = u_domain[0] + u_norm * (u_domain[1] - u_domain[0]) 
        v = v_domain[0] + v_norm * (v_domain[1] - v_domain[0])

        # Evaluate 3D position
        position = rs.EvaluateSurface(surface, u, v)

        # Small random initial velocity
        vx = random.uniform(-0.5, 0.5)
        vy = random.uniform(-0.5, 0.5)
        vz = random.uniform(-0.1, 0.1)
        velocity = (vx, vy, vz) # Small random velocity pertubation

        # Create agent instance
        agent = Agent(
            id=i,
            position=position,
            velocity=velocity,
            surface=surface,
            slope_weight=slope_weight,
            curvature_weight=curvature_weight
        )

        # Store UV and grid info internally for updates
        agent.uv = (u_norm, v_norm)
        agent.heightmap = heightmap
        agent.U_grid = U_grid
        agent.V_grid = V_grid

        agents.append(agent)

    return agents


# --------------------------------------------------------------------------
# Grasshopper script instance
# --------------------------------------------------------------------------
class MyComponent(Grasshopper.Kernel.GH_ScriptInstance):
    """Persistent agent storage across Grasshopper runs."""
    def RunScript(self,
            num_agents,
            reset,
            surface,
            heightmap,
            U_grid,
            V_grid,
            slope_weight,
            curvature_weight):

        # Convert GH wrapper or GUID to Rhino surface
        surface_geom = getattr(surface, "Geometry", surface) # Unwraps GH_Surface
        try:
            import System
            if isinstance(surface_geom, System.Guid):
                surface_geom = rs.coercesurface(surface_geom) # Converts GUID if needed
        except:
            pass

        # Final type check
        if not isinstance(surface_geom, Rhino.Geometry.Surface):
            raise TypeError(f"Input surface is not a valid Rhino surface. Got {type(surface)}") # Safety check

        # Only build agents on reset or first run
        if reset or not hasattr(self, "agents"):
            self.agents = build_agents(
                num_agents=num_agents,
                surface=surface_geom,
                heightmap=heightmap,
                U_grid=U_grid,
                V_grid=V_grid,
                slope_weight=slope_weight,
                curvature_weight=curvature_weight
            )

        # Return persistent agent list
        return self.agents