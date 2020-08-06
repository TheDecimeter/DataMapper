# DataMapper
GIMP plugin to map data points/values to a mercator projection with some projection skewing options.

This plugin isn't well tested and is mostly provided at the moment for code samples.

This plugin requires CSVs with data. These must be separated by COMMA, not space, tab, or whatever else people may use.

This repo includes several files:
- The plugin
  - MercatorPlot.py This does the actual work
- Sample Data Files (Census Data for Migrations to Utah)
  - Coordinates for State/County (Region/Subregion)
  - Values (migration counts) from regions
  - State abbreviations (Preferred Region Names)
  - Anchor Points (points of Texas, Florida, Maine, and Washington)
  - Alternate Indices (which tell the plugin which collumns it can find data in)

To use this plugin:
- Move the plugin file (the python script: MercatorPlot.py) to GIMP's plugin folder and start/restart Gimp.
- You can run the plugin at any time by creating a new image and going to Filters > Render > Data Points (but you probably don't want to do this yet)
- Setup the image to show the plugin how you want your data mapped:
  - Create a new image. The resolution you specify will specify the size of your plotted data (of course, projection skewing might not make it exact). It is recommended that you start with a small resolution to speed up rendering as you test, then make the resolution twice what you think it would be for the final product.
  - If using skewing for projection, add a new layer to the image (with whatever non transparent color you want), then use the projection tool to adjust its size/shape (the top left corner is really the only thing that matters)
  - If you want something other than the default text, use the text tool to add some text that looks like what you want, the plugin will try to copy most of its attributes)
  - Set the foreground and background colors. The brush colors, the primary color is used for the top of the meter, the secondary is the bottom.
- Go to Filters > Render > Data Points to open the plugin's dialog.
- Setup the plugin:
  - Region,Subregion,Lat,Long CSV is a required file that contains the data for where locations are physically (in the samples the region/subregion are state and county)
  - Region,Subregion,Value CSV is a required file that contains the value to be mapped
  -  _You can only include items which conform to a specific regex pattern if you wish, (Eg, to exclude Utah, I use "^(Utah.+|(?!Utah).*)$@.*")
  - Region,Preferrred Name,Subregion,Preferred Name CSV is an optional file for renaming regions (I use this to abbreviate states so names match across the first two CSVs)
  - Alignment Point Name,Lat,Long CSV is an optional file for creating anchor points for aligning a map image by hand (obvious physical features of a map, like Florida's tip)
  - Alternate Indices for above files CSV is an option file. If you don't have your files ordered with data in the columns outlined the name (eg: Region,Subregion, ...) you can identify the proper columns in this file)
  - Mimmic Distortion is a layer with the projection skewing you want to mimmic.
  -  _Distort data height if you want the value bars to shrink in height as they go back
  -  _Distort data width if youwant the value bars to have less width as they go back
  - Minimum Distance before points are combined is how close two points can be before they count as a single point
  - Mimmic Text is a layer you may have set up if you don't want to use the default text format
  -  _Display text for top N data points
      - Set to 0 if you don't want text numbers over your locations
      - Set to -1 if you want text numbers over all of your locations
      - Set to a positive number if you want text numbers over your highest value locations (eg top 10). Note, this only ranks located data.
      - Note, if you use a positive number, text is always drawn over the bars, if you use -1, text is mixed into the bars based on that data point's depth
      - If this is not 0, unlocated data will always have a text label.
      - Creating text takes a while, best of this is 0 while making sure you like where how the bars look.
  - Value of scale meter, What is the max value, if this is 0, the max value will be whatever the max found value is in located data (maybe run this first, with 0, then make a scale value with a round number higher than the given scale value)
  -  _Pixel height of biggest meter, how tall, in pixels is the largest bar, if this is 0, bars won't be drawn, the smallest meter height is always 1
  -  _Pixel width of biggest meter, how wide is the largest bar
  -  _Pixel width of smallest meter, how small the smallest meter is
  -  _Meter blur, the vertical blur of meters (note that small meters are never blurred), 0 if no blur is desired
  -  _Border opacity, How opaque the bar outline should be, 0 if no outline is desired
  -  _Border color, The color of the bar's border

Note that when you run the script, a window might pop up with warnings, this is likely because the CSVs you provided have unparsable lines (like titles, labels, and footnotes). This is fine however GIMP will give up printing these messages, if you think you may be missing a serious error message, go to windows, and open the error console).



