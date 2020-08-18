from landlab.grid.mappers import map_link_vector_components_to_node

# imports
import numpy as np
import matplotlib.pyplot as plt
from landlab import RasterModelGrid, imshow_grid
from landlab.components import TidalFlowCalculator
from landlab.io import read_esri_ascii
from landlab.grid.mappers import map_max_of_link_nodes_to_link

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

tidal_period = 12.5 * 3600.0  # tidal period in seconds
tidal_range = 3.1  # tidal range in meters
tidal_rangev = 2 #tidal range of veg in meters
roughness_w = 0.02  # Manning's n water
roughness_v = 0.2 #manning's n for veg
mean_sea_level = 0.0  # mean sea level in meters
mwd = 0.01  # minimum depth for water on areas higher than low tide water surface, meters
nodata_code = 999  # code for a DEM cell with no valid data

# Read the DEM to create a grid and topography field
(grid, z) = read_esri_ascii('zSW3.asc', name='topographic__elevation')

#need to create vegetation grid
veg = grid.add_zeros('vegetation',at='node');
veg[z<0] = 1;
veg_atlink = grid.map_max_of_link_nodes_to_link('vegetation')
print(veg_atlink)

# Configure boundaries: any nodata nodes, plus any nodes higher than mean high tide
grid.status_at_node[z==nodata_code] = grid.BC_NODE_IS_CLOSED
grid.status_at_node[z>1.8] = grid.BC_NODE_IS_CLOSED
boundaries_above_msl = np.logical_and(grid.status_at_node==grid.BC_NODE_IS_FIXED_VALUE, z > 0.0)
grid.status_at_node[boundaries_above_msl] = grid.BC_NODE_IS_CLOSED

print('pre tfc:')
print(grid.at_node.keys())
print(grid.at_link.keys())


#variable rougness as field in grid
roughness_at_nodes = roughness_w + np.zeros(z.size)
roughness_at_nodes[z < 0.0] = roughness_v #or roughness_at_nodes[veg] = roughness_v
roughness = grid.add_zeros('roughness', at='link')
map_max_of_link_nodes_to_link(grid, roughness_at_nodes, out=roughness)
# Instantiate a TidalFlowCalculator component
tfc = TidalFlowCalculator(
        grid,
        tidal_period=tidal_period,
        tidal_range=tidal_range,
        roughness='roughness',
        mean_sea_level=mean_sea_level,
        min_water_depth=mwd,
)
tau_cr = 0.2 #Critical stress for unvegetated areas
tau_crv = 0.5  #Critical stress for vegetated areas
tcrgradeint = 0.2; # linear increase in tcr below MLW [pa/m]
mud_erodability = (10**-5)*24*3600;  # mud erodability kg/m2/day!!!

#adding in new grids
rate = tfc.calc_tidal_inundation_rate()
grid.add_field('tidal_innundation_rate',rate,at = 'node',units='m/s')

tfc._calc_effective_water_depth()
grid.add_field('effective_water_depth',tfc._water_depth,at='node',units='m')

tfc.run_one_step()
print(tfc._diffusion_coef_at_links) #we can get out more variables

topo = grid.at_node['topographic__elevation']

msl = tfc._mean_sea_level
dHW = np.maximum(0,topo+msl+tfc._tidal_half_range)
dHW[topo==999] = 0;

ftide = np.minimum(1,np.maximum(10^-3, dHW/tidal_range))
#ftide[topo==999] = 999
grid.add_field('hydroperiod',ftide,at='node',units='m')
grid.add_field('water_depth_at_MHW',dHW,at='node',units='m')

lev_an = -topo-msl #water depth with respect to MSL
print(lev_an)
grid.add_field('lev_at_node',lev_an,at = 'node')
lev_atlink = grid.map_max_of_link_nodes_to_link('lev_at_node')

taucr = grid.add_zeros('tau_cr',at='link') + tau_cr
taucr[veg_atlink==1] = tau_crv

xi = -lev_atlink-tidal_rangev/2
xi[xi<0] = 0
taucr += xi*tcrgradeint


fupeak = np.pi/2
#total sed erosion for loop
ntdcy = 10 #number of tidal cycles
E = grid.add_zeros('Erosion',at = 'link')
print(mud_erodability)
print(" ")
for i in range(ntdcy):
    utide = grid.at_link['flood_tide_flow__velocity']*fupeak*np.sin(i/ntdcy * np.pi/2) #intra-tidal velocity
    tauc = 1025*9.81*roughness**2 * utide**2 * tfc._water_depth_at_links**(-1/2)
    E += 1/(ntdcy+1)*mud_erodability*(np.sqrt(1+(tauc/taucr)**2)-1)
    print(max(E))

print(grid.at_link.keys())    
#print(np.maximum(E))
