# ---------------------------------------------------------------------------
# Component 3: Agent Simulator / Tick (Persistent)
# ---------------------------------------------------------------------------
# Purpose: Advances the simulation for all agents created in Component 2.
# Inputs:
#   - agents : list of Agent instances (from Component 2)
#   - tick   : trigger to advance simulation
# Outputs:
#   - P : points representing agent positions
#   - V : lines representing agent velocities
# ---------------------------------------------------------------------------

import rhinoscriptsyntax as rs
import scriptcontext as sc

# ---------------------------------------------------------------------------
# Use scriptcontext.sticky for persistent storage
# ---------------------------------------------------------------------------
if "agents_storage" not in sc.sticky: # Checks whether component has already stored agents from a previous solution
    if agents is None:
        sc.sticky["agents_storage"] = []  # Empty list is created if nothing is connected
    else:
        sc.sticky["agents_storage"] = agents if isinstance(agents, list) else [agents] # Stores agents in list
        # Note: If a list already exists, the agents are stored directly. If only a single agent exist, it is wrapped in a list. 
else:
    # If new agents are connected, update storage
    if agents is not None: # Only overwrite stored agents if a new agent input is provided
        sc.sticky["agents_storage"] = agents if isinstance(agents, list) else [agents] # Preserves agents if nothing changes upstream

# Retrieve stored agents
agents_storage = sc.sticky["agents_storage"]

# ---------------------------------------------------------------------------
# STEP SIMULATION: update each agent if tick is pressed
# ---------------------------------------------------------------------------
if tick:
    for agent in agents_storage:
        # Each agent has heightmap, U_grid, V_grid stored internally
        agent.update()  # Performs sense -> decide -> move

# ---------------------------------------------------------------------------
# VISUALIZATION
# ---------------------------------------------------------------------------
P = []  # Points representing agent positions
V = []  # Lines representing velocity vectors

for agent in agents_storage:
    # Add point at agent's current position
    P.append(rs.AddPoint(agent.position[0], agent.position[1], agent.position[2]))
    
    # Compute end point for velocity vector
    end_point = (
        agent.position[0] + agent.velocity[0],
        agent.position[1] + agent.velocity[1],
        agent.position[2] + agent.velocity[2]
    )
    # Add line representing velocity vector
    V.append(rs.AddLine(agent.position, end_point))

# ---------------------------------------------------------------------------
# OUTPUTS
# ---------------------------------------------------------------------------
# P : list of points representing agent positions
# V : list of lines representing agent velocities
