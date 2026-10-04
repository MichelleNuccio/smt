### Overview

I am making a sandbox in the style of the course simmodeltwin.net. There should be more information in the agents.md about what this specifically means, but in short it is a web-based simulation that contains some data, some rule for how to apply that data, a clock for running the rule forward in time, and some sliders that will let us change the variables and assumptions in the dataset. If an agents.md with more context is missing from this session, please do not complete this prompt, and direct the person running this to tutorial 4. 

### data

In data/Original, you can find:
- 2015_street_tree_census -> this is a tabular dataset of street trees in upper manhattan with associated data
- nycb2010_subset_um -> this is a subset of the 2010 nyc census blocks for just upper manhattan, where our street tree dataset also is
- queens_tree_equations.csv -> this is a list of equations for how to generate new data about each tree from what we have, specific to each tree species. For example, "crown_diameter_from_dbh" will give you the equation form and a series of coefficients for how to derive the crown diameter of a tree from its dbh. 

Any new processed datasets should go in data/Processed. 

### objectives

This is a simplified version of the way that the nyc parks department estimates the ecological benefits of street trees, per [here](https://www.nycgovparks.org/tree-map/learn/benefits). To keep things simple, I would just like to do this for stormwater interception. 

For stormwater interception, I found the formula: canopy × rain × 0.0254 (inches to meters) × interception × 264.17 (cubic meters to gallons conversion factor). The parks methodology uses 41 inches of rain annually, which was observed at JFK for the year 2000, and I am using 0.15 (15%) as a constant for interception - how much rain a tree's leaves catch. The actual methodology is a lot more complicated, but 15% is what one Callery pear caught in a field study in Davis, California (Xiao et al. 2000); a cork oak in the same study caught 27%.

However, instead of using constants, I would like if those variables (rain, interception, etc) are editable on the interactive. 

### data prep - the rule

Below is a chart sketch of what the final created data should look like. In the class parlance, this is the "rule". The first five columns should come from the original files and do not change. The last three are what the page works out for every tree, every year. The page has to do those, since the rain and the interception are sliders, and the stormwater changes whenever one of them moves. The notes below the table say where each column comes from.

| address | status | species | dbh (in) | block | crown (m) | canopy (m²) | stormwater (gal/yr) |
|---|---|---|---|---|---|---|---|
| 1 Morningside Dr | Alive | pin oak | 18 | 10197011002 | 12.3 | 120 | 4,937 |
| 401 W 118 St | Alive | Callery pear | 11 | 10207011001 | 8.4 | 55 | 2,278 |
| 110 St Nicholas Ave | Alive | honeylocust | 9 | 10218002000 | 9.0 | 64 | 2,645 |
| 131 St Nicholas Ave | Alive | American linden | 7 | 10218004002 | 5.5 | 23 | 965 |
| 421 W 118 St | Dead | planting site | | 10207011001 | | | |
| 400 Riverside Dr | Stump | planting site | | 10199001002 | | | |

- **address**: from the census. The map uses the census latitude and longitude.
- **status**: keep the `Alive` trees. The `Dead` and `Stump` rows become the planting sites (I will describe this later)
- **species**: the species in the census. The equations file only has 21 species. Beyond that, please try to match any given species to its closest relative in the equations file. After that, default to honeylocust - the most common tree in the street trees census.
- **dbh (in)**: the trunk diameter at breast height, from the census. Over 60 inches is a data entry error, so treat it as missing.
- **block**: the census block the tree is in, by point in polygon.
- **crown (m)**: the crown diameter, from the species' equation, with dbh in cm. For the Callery pear it's 0.41182 + 0.28531 × dbh.
- **canopy (m²)**: the crown as a circle, π × (crown ÷ 2)².
- **stormwater (gal/yr)**: canopy × rain (41.0 inches) × 0.0254, which converts inches to meters, × interception (0.15) × 264.17, which converts cubic meters to gallons.

### the run

In the class parlance, the "run" is applying the rule over time. The interactive variables should work like this:
- stormwater interception: per the variables (rainfall, interception), measure the amount of stormwater that a tree intercepts every year from 2015 (start) to 2045 (end)
- growth: using the `age_from_dbh` and `dbh_from_age` equations in `queens_tree_equations.csv`, estimate the growth of each tree per year (age from dbh, then dbh from age + 1 minus dbh from age)
- new plantings: from a `new plantings per year` slider (0 to 100, starting at 0), plant that many new trees every year on the sites currently occupied by dead trees and stumps, chosen at random. Every new tree is a honeylocust, 3 inches dbh when it's planted. Once a site is planted it stays taken, and a tree that dies during the run doesn't open up a new site. (truthfully this method could be improved upon)
- deaths: randomly have a certain percentage of trees not survive everywhere. the i-tree guide says 2.8% a year under age 5, 0.57% after. use those numbers as the default values on the slider.
- rainfall: use the default value of 41 inches, and pick a sensible range for the nyc metro
- interception: use the default value of 0.15, and pick a sensible range based on available info.

### the interactive

Here is an unordered list of what the interactive should have: 
- in the center, a map with the simulation results. on the left is an info panel with a title and a description (that I will explain more in a second,) and on the right is another panel with controls and the clock.
- two views: one showing stormwater interception per tree, and one by census block (for this, you will have to aggregate the trees' individual counts up to the block)
- clock: a playhead that goes from 2015 to 2045, with pause, fast forward and rewind buttons 
- controls: a series of sliders per the above descriptions. 
- title: street tree stormwater interception simulation
- description: an attempt to visualize how street trees act as a network to mitigate stormwater runoff. This is using a simplified version of the nyc parks department's methodology, which uses the USDA Forest Service's i-Tree software. 
- limitations: this sandbox is based on a number of simplifications, including a flat figure for stormwater interception, a lack of awareness of local drainage and topography conditions that would impact runoff mitigation, a simplified model of where trees die and where they are planted, no knowledge of broader networks of policy and care that support the nyc street tree system, and others.
- citations: all datasets used in the sandbox should be briefly described and linked to here


Okay, that is all, please let me know if you have any questions or if anything is not clear.