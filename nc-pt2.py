"""
THIS SCRIPT COMPARES THE INDEX VALUES OF TWO YEARS AND CREATES A NUMBER OF OUTPUT
FIELDS:
    1.  A NUMERIC VALUE OF HOW MUCH THE INDEX CATEGORY SHIFTED, AND IN WHICH DIRECTION
    2.  A RECLASSIFIED NUMERIC VALUE OF POSITIVE CHANGE, NO CHANGE, OR NEGATIVE CHANGE
    3.  A STRING VALUE STATING WHICH CATEGORY TO WHICH CATEGORY THE RECORD MOVED (I.E. "6 TO 5")

To create an ArcToolbox tool with which to execute this script, do the following.
1   In  ArcMap > Catalog > Toolboxes > My Toolboxes, either select an existing toolbox
    or right-click on My Toolboxes and use New > Toolbox to create (then rename) a new one.
2   Drag (or use ArcToolbox > Add Toolbox to add) this toolbox to ArcToolbox.
3   Right-click on the toolbox in ArcToolbox, and use Add > Script to open a dialog box.
4   In this Add Script dialog box, use Label to name the tool being created, and press Next.
5   In a new dialog box, browse to the .py file to be invoked by this tool, and press Next.
6   In the next dialog box, specify the following inputs (using dropdown menus wherever possible)
    before pressing OK or Finish.
        DISPLAY NAME                                       DATA TYPE       PROPERTY>DIRECTION>VALUE
        Input Shapefile for year 1 and 2                   Shapefile       Input
        Index field for year 1                             Field           Input > Obtained from Input Shapefile for year 1
        Index field for year 2                             Field           Input > Obtained from Input Shapefile for year 2
        2-digit date of year 1                             String          Input > Default '00'
        2-digit date of year 2                             String          Input > Default '10'
        Output Shapefile                                   Shapefile       Output

   To later revise any of this, right-click to the tool's name and select Properties.
"""

# Import necessary modules
import sys, os, string, math, arcpy, traceback

# Allow output file to overwrite any existing file of the same name
arcpy.env.overwriteOutput = True

try:

    # Request user inputs, name variables
    nameOfInputShapefile1  = arcpy.GetParameterAsText(0)
    yearField1             = arcpy.GetParameterAsText(1)
    yearField2             = arcpy.GetParameterAsText(2)
    yearOfData1            = arcpy.GetParameterAsText(3)
    yearOfData2            = arcpy.GetParameterAsText(4)
    nameOfOutputShapefile  = arcpy.GetParameterAsText(5)

    # Report input and output files
    arcpy.AddMessage('\n' + "The input shapefile name for year 1 is " + nameOfInputShapefile1)

    arcpy.AddMessage("The output shapefile name is " + nameOfOutputShapefile)
    arcpy.AddMessage("This is a report for the change in index score for years '" + yearOfData1 + " and '" + yearOfData2 + "\n")

    # Replicate the input shapefile
    arcpy.Copy_management(nameOfInputShapefile1, nameOfOutputShapefile)

    """ STEP ONE: CALCULATE INDEX CATEGORY SHIFT """
    # Add a new field called "CHNGE + years of comparison"
    chngeName = ("CHNGE" + str("_" + yearOfData1) + str(yearOfData2))
    arcpy.AddField_management(nameOfOutputShapefile, chngeName, "FLOAT", 20, 10)

    # Create an enumeration of updatable records from the shapefile's attribute table
    enumerationOfRecords = arcpy.UpdateCursor(nameOfOutputShapefile)

    for nextRecord in enumerationOfRecords:
        #Subtract year 1 value from year 2 value
        nextYear1   = nextRecord.getValue(yearField1)
        nextYear2   = nextRecord.getValue(yearField2)
        indexChange = nextYear2 - nextYear1
        nextRecord.setValue(chngeName,indexChange)
        enumerationOfRecords.updateRow(nextRecord)

    # Add message
    arcpy.AddMessage("Change of index score between years '" + str(yearOfData1) + " and '" + str(yearOfData2) + " calculated")

        # Delete row and update cursor objects to avoid locking attribute table
    del nextRecord
    del enumerationOfRecords

    """ STEP TWO: RECLASSIFY POSITIVE CHANGE, NO CHANGE, NEGATIVE CHANGE """
    # Add a new field called "RCLSS + years of comparison"
    reclassName = ("RCLSS" + str("_" + yearOfData1) + str(yearOfData2))
    arcpy.AddField_management(nameOfOutputShapefile, reclassName, "FLOAT", 20, 10)

    # Create an enumeration of updatable records from the shapefile's attribute table
    enumerationOfRecords = arcpy.UpdateCursor(nameOfOutputShapefile)

    for nextRecord in enumerationOfRecords:
        #Reclassify values to -1, 0, and 1
        changeValue   = nextRecord.getValue(chngeName)
        if changeValue < 0:
            reclassValue = -1
            nextRecord.setValue(reclassName,reclassValue)
            enumerationOfRecords.updateRow(nextRecord)
        elif changeValue == 0:
            reclassValue = 0
            nextRecord.setValue(reclassName,reclassValue)
            enumerationOfRecords.updateRow(nextRecord)
        else:
            reclassValue = 1
            nextRecord.setValue(reclassName,reclassValue)
            enumerationOfRecords.updateRow(nextRecord)

    # Add message
    arcpy.AddMessage("Positive/No/Negative change reclassification between years '" + str(yearOfData1) + " and '" + str(yearOfData2) + " calculated")

        # Delete row and update cursor objects to avoid locking attribute table
    del nextRecord
    del enumerationOfRecords

    """ STEP THREE: REPORT INDEX CHANGE IN A STRING """
    # Add a new field called "RCLSS + years of comparison"
    reportName = ("RPRT" + str("_" + yearOfData1) + str(yearOfData2))
    arcpy.AddField_management(nameOfOutputShapefile, reportName, "TEXT")

    # Create an enumeration of updatable records from the shapefile's attribute table
    enumerationOfRecords = arcpy.UpdateCursor(nameOfOutputShapefile)

    for nextRecord in enumerationOfRecords:
        #Report index value change
        yearValue1   = nextRecord.getValue(yearField1)
        yearValue2   = nextRecord.getValue(yearField2)
        reportValue  = (str(yearValue1) + " to " + str(yearValue2))
        nextRecord.setValue(reportName,reportValue)
        enumerationOfRecords.updateRow(nextRecord)

    # Add message
    arcpy.AddMessage("Index value change between years '" + str(yearOfData1) + " and '" + str(yearOfData2) + " reported" + "\n")

        # Delete row and update cursor objects to avoid locking attribute table
    del nextRecord
    del enumerationOfRecords

    """ STEP FOUR: SPATIAL ANALYSIS """
    nameOfOutputShapefile2 = nameOfOutputShapefile[:-4] + "_SA"

    # Replicate the output shapefile
    arcpy.Copy_management(nameOfOutputShapefile, nameOfOutputShapefile2)

    secondOutput = (nameOfOutputShapefile2 + "_rclss")
    arcpy.ClustersOutliers_stats(nameOfOutputShapefile2, reclassName,secondOutput,
                             "INVERSE_DISTANCE","EUCLIDEAN_DISTANCE",
                             "NONE","", "","")

except Exception as e:
    # If unsuccessful, end gracefully by indicating why
    arcpy.AddError('\n' + "Script failed because: \t\t" + e.message )
    # ... and where
    exceptionreport = sys.exc_info()[2]
    fullermessage   = traceback.format_tb(exceptionreport)[0]
    arcpy.AddError("at this location: \n\n" + fullermessage + "\n")
