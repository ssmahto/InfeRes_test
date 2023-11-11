
# IMPORTING LIBRARY

import csv
import os
import utm
import numpy as np
from osgeo import gdal, gdal_array
import matplotlib.pyplot as plt


# HELPER FUNCTION
def pick(c, r, mask): # (c_number, r_number, an array of 1 amd 0) 
    filled = set()
    fill = set()
    fill.add((c, r))
    width = mask.shape[1]-1
    height = mask.shape[0]-1
    picked = np.zeros_like(mask, dtype=np.int8)
    while fill:
        x, y = fill.pop()
        if y == height or x == width or x < 0 or y < 0:
            continue
        if mask[y][x] == 1:
            picked[y][x] = 1
            filled.add((x, y))
            west = (x-1, y)
            east = (x+1, y)
            north = (x, y-1)
            south = (x, y+1)
            if west not in filled:
                fill.add(west)
            if east not in filled:
                fill.add(east)
            if north not in filled:
                fill.add(north)
            if south not in filled:
                fill.add(south)
    return picked

def curve(res_name, max_wl, point, boundary, dem_file_path): 
    # =====================================================  INPUT PARAMETERS
    bc = boundary
    pc = point
    coords = bc + pc
    utm_coords = np.array([utm.from_latlon(coords[i + 1], coords[i]) for i in range(0, len(coords), 2)])
    # Bounding box of the reservoir [ulx, uly, lrx, lry]
    bbox = np.array([utm_coords[0,0], utm_coords[0,1], utm_coords[1,0], utm_coords[1,1]], dtype=np.float32) 
    res_point = np.array([utm_coords[2,0], utm_coords[2,1]], dtype=np.float32)
    # 30m equivalent distance in degree
    #dist30m= 0.01745329252  
    xp = round(abs(res_point[0]-bbox[0])/30)
    yp = round(abs(res_point[1]-bbox[1])/30)
    # Maximum reservoir water level                            
    curve_ext = max_wl + 10 # to expand the curve  
    
    # CREATING E-A-S RELATIONSHOP
    # clipping DEM by the bounding box
    print("Clipping DEM by the bounding box ...") 
    dem = gdal.Open(dem_file_path) 
    
    # Changing path to the desired reservoir
    os.chdir(os.getcwd() + "/Outputs")
    res_dem_file = res_name+"DEM.tif"
    dem = gdal.Translate(res_dem_file, dem, projWin = bbox)   #bbox=bc
    dem = None 
    
    # isolating the reservoir
    dem_bin = gdal_array.LoadFile(res_dem_file)
    #------------------ Visualization <Start>
    plt.figure()
    plt.imshow(dem_bin, cmap='jet')
    plt.colorbar()
    dem_bin[np.where(dem_bin > curve_ext)] = 0
    dem_bin[np.where(dem_bin > 0)] = 1
    res_iso = pick(xp, yp, dem_bin)
    output = gdal_array.SaveArray(res_iso.astype(gdal_array.numpy.float32), 
                                  "res_iso.tif", format="GTiff", 
                                  prototype = res_dem_file)
    output = None
    
    # finding the lowest DEM value in the reservoir extent
    res_dem = gdal_array.LoadFile(res_dem_file)
    res_dem[np.where(res_iso == 0)] = 9999
    min_dem = np.nanmin(res_dem)
    
    # caculating reservoir surface area and storage volume 
    # coresponding to each water level
    results = [["Level (m)", "Area (skm)", "Storage (mcm)"]]
    pre_area = 0
    tot_stor = 0 
    for i in range(min_dem, curve_ext): 
        level = i
        water_px = gdal_array.LoadFile(res_dem_file)
        water_px[np.where(res_iso == 0)] = 9999
        water_px[np.where(res_dem > i)] = 0 
        water_px[np.where(water_px > 0)] = 1
        area = np.nansum(water_px)*9/10000
        storage = (area + pre_area)/2
        tot_stor += storage
        pre_area = area   
        results = np.append(results, [[level, round(area,4), round(tot_stor,4)]], 
                            axis=0)
    
    # saving output as a csv file
    with open("Curve.csv","w", newline='') as my_csv:
        csvWriter = csv.writer(my_csv)
        csvWriter.writerows(results)
    
# ==================== Plot the DEM-based Level-Storage curve
    
    data = results[1:, :]
    data = np.array(data, dtype=np.float32)
    # Extract column 2 and 3 from the array
    column_1 = data[:, 0]
    column_3 = data[:, 2]
    # Create the scatter plot
    plt.figure()
    plt.scatter(column_1, column_3, s=5, c='red')
    # Set labels and title
    plt.xlabel('Level (m)')
    plt.ylabel('Storage (mcm)')
    plt.title(res_name)
    plt.savefig(res_name+'_storageVSelevation.png', dpi=600, bbox_inches='tight')
    
    return min_dem



