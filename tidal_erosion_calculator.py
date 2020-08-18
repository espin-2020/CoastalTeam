from landlab.grid.mappers import map_link_vector_components_to_node

# imports
import numpy as np
import matplotlib.pyplot as plt
from landlab import RasterModelGrid, imshow_grid
from landlab.components import TidalFlowCalculator
from landlab.io import read_esri_ascii
from landlab.grid.mappers import map_max_of_link_nodes_to_link
from landlab.grid.mappers import map_node_to_cell

def map_velocity_components_to_nodes(grid):
    """Map the velocity components from the links to the nodes, and return the node arrays."""
    ebb_vel_x, ebb_vel_y = map_link_vector_components_to_node(grid, grid.at_link['ebb_tide_flow__velocity'])
    flood_vel_x = -ebb_vel_x
    flood_vel_y = -ebb_vel_y
    ebb_vel = np.sqrt(ebb_vel_x^2 + ebb_vel_y^2)
    flood_vel = -ebb_vel
    return (ebb_vel_x, ebb_vel_y, flood_vel_x, flood_vel_y,ebb_vel, flood_vel)

def plot_tidal_flow(grid, resample=1):
    (ebb_x, ebb_y, flood_x, flood_y) = map_velocity_components_to_nodes(grid)

    # depth
    plt.figure()
    imshow_grid(grid, grid.at_node['mean_water__depth'], cmap='YlGnBu', color_for_closed='g')
    plt.title('Water depth (m)')
    plt.xlabel('Distance (m)')
    plt.ylabel('Distance (m)')

    # down-sample for legible quiver plots if needed
    if resample != 1:
        xr = grid.x_of_node.reshape((grid.number_of_node_rows, grid.number_of_node_columns))[::resample, ::resample]
        yr = grid.y_of_node.reshape((grid.number_of_node_rows, grid.number_of_node_columns))[::resample, ::resample]
        ebb_xr = ebb_x.reshape((grid.number_of_node_rows, grid.number_of_node_columns))[::resample, ::resample]
        ebb_yr = ebb_y.reshape((grid.number_of_node_rows, grid.number_of_node_columns))[::resample, ::resample]
        fld_xr = flood_x.reshape((grid.number_of_node_rows, grid.number_of_node_columns))[::resample, ::resample]
        fld_yr = flood_y.reshape((grid.number_of_node_rows, grid.number_of_node_columns))[::resample, ::resample]
    else:
        xr = grid.x_of_node
        yr = grid.y_of_node
        ebb_xr = ebb_x
        ebb_yr = ebb_y
        fld_xr = flood_x
        fld_yr = flood_y
        
    # ebb tide
    plt.figure()
    imshow_grid(grid, grid.at_node['topographic__elevation'])
    plt.quiver(xr, yr, ebb_xr, ebb_yr)
    plt.title('Ebb Tide')
    plt.xlabel('Distance (m)')
    plt.ylabel('Distance (m)')

    ebb_vel_magnitude = np.sqrt(ebb_x * ebb_x + ebb_y * ebb_y)
    plt.figure()
    imshow_grid(grid, ebb_vel_magnitude, cmap='magma', color_for_closed='g')
    plt.title('Ebb Tide Velocity Magnitude (m/s)')
    plt.xlabel('Distance (m)')
    plt.ylabel('Distance (m)')

    # flood tide
    plt.figure()
    imshow_grid(grid, grid.at_node['topographic__elevation'])
    plt.quiver(xr, yr, fld_xr, fld_yr)
    plt.title('Flood Tide')
    plt.xlabel('Distance (m)')
    plt.ylabel('Distance (m)')

    plt.figure()
    flood_vel_magnitude = np.sqrt(flood_x * flood_x + flood_y * flood_y)
    imshow_grid(grid, flood_vel_magnitude, cmap='magma', color_for_closed='g')
    plt.title('Flood Tide Velocity Magnitude (m/s)')
    plt.xlabel('Distance (m)')
    plt.ylabel('Distance (m)')
    
def map_node2cell_addGrid(grid,var1,var2): #takes a grid, plus the variable you want to map to cell, and the string name
    a = grid.map_node_to_cell(var1)
    return grid.add_field(var2, a, at='cell')
    
def populateGrids(grid,tfc):
    rate = tfc.calc_tidal_inundation_rate()
    grid.add_field('tidal_innundation_rate',rate,at = 'node',units='m/s')
    map_node2cell_addGrid(grid,rate,'tidal_innundation_rate_cell')

    tfc._calc_effective_water_depth()
    grid.add_field('effective_water_depth',tfc._water_depth,at='node',units='m')
    map_node2cell_addGrid(grid,tfc._water_depth,'effective_water_depth_cell')
    
    tfc.run_one_step()

    topo = grid.at_node['topographic__elevation']
    map_node2cell_addGrid(grid,topo,'topographic_elevation_cell')
    
    msl = tfc._mean_sea_level
    dHW = np.maximum(0,topo+msl+tfc._tidal_half_range)
    dHW[topo==999] = 0;

    ftide = np.minimum(1,np.maximum(10^-3, dHW/tidal_range))
    #ftide[topo==999] = 999
    grid.add_field('hydroperiod',ftide,at='node',units='m')
    grid.add_field('water_depth_at_MHW',dHW,at='node',units='m')
    map_node2cell_addGrid(grid,ftide,'hydroperiod_cell')
    map_node2cell_addGrid(grid,dHW,'water_depth_at_MHW_cell')
    
    lev_an = -topo-msl #water depth with respect to MSL
    grid.add_field('lev_at_node',lev_an,at = 'node')
    lev_atlink = grid.map_max_of_link_nodes_to_link('lev_at_node')
    map_node2cell_addGrid(grid,lev_an,'lev_at_cell')

    taucr = grid.add_zeros('tau_cr',at='link') + tau_cr
    taucr[veg_atlink==1] = tau_crv
    map_node2cell_addGrid(grid,taucr,'tau_cr_cell')
    
    ebb = grid.at_link['ebb_tide_flow__velocity']
    map_node2cell_addGrid(grid,ebb,'ebb_tide_flow__velocity_cell')
    map_node2cell_addGrid(grid,-ebb,'flood_tide_flow__velocity_cell')
    
    grid.add_field('water_depth_at_link',tfc._water_depth_at_links,at = 'link',units='m')
    map_node2cell_addGrid(grid,tfc._water_depth_at_links,'water_depth_at_cell')
    
