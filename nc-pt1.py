"""
THIS SCRIPT CREATES AN INDEX OF NEIGHBORHOOD CHANGE USING USER SPECIFIED INDICATORS:
    1. CALCULATE Z-SCORE FOR EACH INDICATOR
    2. CALCULATE NEGATIVE Z-SCORE FOR INDICATORS THAT SHOULD DETRACT FROM SCORE (I.E. VACANCY RATE)
    3. ADD INDICATORS TOGETHER FOR RAW SCORE
    4. DEFINE CLASSIFICATION METHOD
    5. ASSIGN EACH RECORD AN INDEX SCORE FROM 1-6

FOR COMPARATIVE PURPOSES, THIS SCRIPT IS SET UP SO THAT MULTIPLE YEARS OF DATA CAN BE
IN THE SAME SHAPEFILE; IN OTHER WORDS, ONE SHAPEFILE CAN BE RUN THROUGH THE TOOL MULTIPLE TIMES
ON DIFFERENT YEARS OF VARIABLES WITHOUT ERRORS.

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
        Input Shapefile                                    Shapefile       Input
        Fields used as indicators in index                 Field           Input > MultiValue: Yes > Obtained from Input Shapefile
        2-digit date of variable data                      String          Input > Default '10'
        Output Shapefile                                   Shapefile       Output
        Indicators that should subtract from index         Field           Input > Type: Optional > MultiValue: Yes > Obtained from Input Shapefile
        score if high (ex. high vacancy rates)
        Choose Index Classification Method                 String          Input > Filter: Value List (Quantile, Equal Interval)
        Choose number of classes                           Double          Input

   To later revise any of this, right-click to the tool's name and select Properties.
"""

# Import necessary modules
import sys, os, string, math, arcpy, traceback

# Allow output file to overwrite any existing file of the same name
arcpy.env.overwriteOutput = True

try:

    # Request user inputs, name variables
    nameOfInputShapefile  = arcpy.GetParameterAsText(0)
    varFields             = arcpy.GetParameterAsText(1)
    yearOfData            = arcpy.GetParameterAsText(2)
    nameOfOutputShapefile = arcpy.GetParameterAsText(3)
    negVariables          = arcpy.GetParameterAsText(4)
    classificationMethod  = arcpy.GetParameterAsText(5)
    classNumber           = arcpy.GetParameterAsText(6)

    varList = varFields.split(";")  # a list of all variables for index
    negList = negVariables.split(";")  # a list of the variables from varList that should be multiplied by -1 to detract from raw score (ie vacancy rate)
    zScoreList = []  # a list of the variable fields that will count towards raw score (combination of z-scores and some z-scores * -1)
    nameOfOutputShapefileTemp = nameOfOutputShapefile[:-4] + "_temp.shp"

    # Report input and output files
    arcpy.AddMessage('\n' + "The input shapefile name is " + nameOfInputShapefile)
    arcpy.AddMessage("The output shapefile name is " + nameOfOutputShapefile)
    arcpy.AddMessage("This is an index for year '" + yearOfData)
    arcpy.AddMessage("The variables used as indicators in the index are " + str(varList) + "\n")

    # Create function to calculate mean (source: http://arcpy.wordpress.com/2012/02/01/calculate-a-mean-value-from-a-field/)
    def calculate_mean_value(table, field):
        stats_table = r"in_memory\stats"
        arcpy.Statistics_analysis(table, stats_table, [[field, "MEAN"]])
        mean_field = "MEAN_{0}".format(field)
        cursor = arcpy.SearchCursor(stats_table, "", "", mean_field)
        row = cursor.next()
        mean_value = row.getValue(mean_field)
        del cursor
        return mean_value

    # Create function to calculate standard deviation
    def calculate_STD_value(table, field):
        stats_table = r"in_memory\stats"
        arcpy.Statistics_analysis(table, stats_table, [[field, "STD"]])
        STD_field = "STD_{0}".format(field)
        cursor = arcpy.SearchCursor(stats_table, "", "", STD_field)
        row = cursor.next()
        STD_value = row.getValue(STD_field)
        del cursor
        return STD_value

    # Create function to calculate range
    def calculate_range_value(table, field):
        stats_table = r"in_memory\stats"
        arcpy.Statistics_analysis(table, stats_table, [[field, "RANGE"]])
        RNG_field = "RANGE_{0}".format(field)
        cursor = arcpy.SearchCursor(stats_table, "", "", RNG_field)
        row = cursor.next()
        RNG_value = row.getValue(RNG_field)
        del cursor
        return RNG_value

    # Create function to calculate minimum value
    def calculate_MIN_value(table, field):
        stats_table = r"in_memory\stats"
        arcpy.Statistics_analysis(table, stats_table, [[field, "MIN"]])
        MIN_field = "MIN_{0}".format(field)
        cursor = arcpy.SearchCursor(stats_table, "", "", MIN_field)
        row = cursor.next()
        MIN_value = row.getValue(MIN_field)
        del cursor
        return MIN_value

    # Create function to calculate count of items
    def calculate_COUNT_value(table, field):
        stats_table = r"in_memory\stats"
        arcpy.Statistics_analysis(table, stats_table, [[field, "COUNT"]])
        COUNT_field = "COUNT_{0}".format(field)
        cursor = arcpy.SearchCursor(stats_table, "", "", COUNT_field)
        row = cursor.next()
        COUNT_value = row.getValue(COUNT_field)
        del cursor
        return COUNT_value

    # Replicate the input shapefile
    arcpy.Copy_management(nameOfInputShapefile, nameOfOutputShapefileTemp)

    """ STEP ONE: CALCULATE Z-SCORE OF EACH INDICATOR FIELD """
    # Process each variable in the user-defined variable list
    for variable in varList:
        arcpy.AddMessage("Processing: " + variable)

        # Concatenate the list order number to the field name and add a new field called "MEAN"
        meanName = ("MEAN" + str(varList.index(variable)) + str("_" + yearOfData))
        arcpy.AddField_management(nameOfOutputShapefileTemp, meanName, "FLOAT", 20, 10)

        # Concatenate the list order number to the field name and add a new field called "STDDEV"
        stdDevName = ("STDV" + str(varList.index(variable)) + str("_" + yearOfData))
        arcpy.AddField_management(nameOfOutputShapefileTemp, stdDevName, "FLOAT", 20, 10)

        # Concatenate the list order number to the field name and add another new field called "ZSCORE"
        zName = ("ZSCR" + str(varList.index(variable)) + str("_" + yearOfData))
        arcpy.AddField_management(nameOfOutputShapefileTemp, zName, "FLOAT", 20, 10)

        # Create an enumeration of updatable records from the shapefile's attribute table
        enumerationOfRecords = arcpy.UpdateCursor(nameOfOutputShapefileTemp)

        # Loop through that enumeration, creating mean field column
        for nextRecord in enumerationOfRecords:
            # Calculate sample mean
            mean = (calculate_mean_value(nameOfOutputShapefileTemp, variable))
            nextRecord.setValue(meanName,mean)
            enumerationOfRecords.updateRow(nextRecord)
            # Calculate standard deviation
            standardDev = (calculate_STD_value(nameOfOutputShapefileTemp, variable))
            nextRecord.setValue(stdDevName,standardDev)
            enumerationOfRecords.updateRow(nextRecord)
            # Retrieve the row value, mean, and standard deviation
            nextVar   = nextRecord.getValue(variable)
            nextMean   = nextRecord.getValue(meanName)
            nextStdDev = nextRecord.getValue(stdDevName)
            # Calculate and record z-score
            zScore   = (nextVar - nextMean) / nextStdDev
            nextRecord.setValue(zName,zScore)
            enumerationOfRecords.updateRow(nextRecord)

        # add the zscore field name for this variable to the zScoreList
        zScoreList.append(zName)

        # Delete row and update cursor objects to avoid locking attribute table
        del nextRecord
        del enumerationOfRecords

        arcpy.AddMessage("The mean value if this indicator is " + str(mean))
        arcpy.AddMessage("The standard deviation of this indicator is " + str(standardDev))
        arcpy.AddMessage("Z-score calculated" + "\n")


        """ STEP TWO: MAKE THE ZSCORES OF USER CHOSEN VARIABLES NEGATIVE TO DETRACT FROM SCORE """
        if variable in negList:
            # Concatenate the list order number to the field name
            # Add another new field called "ZNEG"
            zNegName = ("ZNEG" + str(varList.index(variable)) + str("_" + yearOfData))
            arcpy.AddField_management(nameOfOutputShapefileTemp, zNegName, "FLOAT", 20, 10)

            # Create an enumeration of updatable records from the shapefile's attribute table
            enumerationOfRecords = arcpy.UpdateCursor(nameOfOutputShapefileTemp)
            for nextRecord in enumerationOfRecords:
                #Multiply z-score by -1
                nextNeg   = nextRecord.getValue(zName)
                calcNegZ   = nextNeg * -1
                nextRecord.setValue(zNegName,calcNegZ)
                enumerationOfRecords.updateRow(nextRecord)

            # add the zscore field name for the negative variable to the zScoreList, and remove the
            # regular zscore field name for this same variable from the list
            zScoreList.append(zNegName)
            zScoreList.remove(zName)

            # Add message
            arcpy.AddMessage("Negative of Z-score calculated" + "\n")

            # Delete row and update cursor objects to avoid locking attribute table
            del nextRecord
            del enumerationOfRecords

    """ STEP THREE: ADD Z-SCORES TOGETHER FOR RAW INDEX SCORE """
    arcpy.AddMessage("These fields are used to calculate the z-score: " + str(zScoreList))
    rawField = ("RAWSCR_" + yearOfData)
    arcpy.AddField_management(nameOfOutputShapefileTemp, rawField, "FLOAT", 20, 10)

    # Create an enumeration of updatable records from the shapefile's attribute table
    enumerationOfRecords = arcpy.UpdateCursor(nameOfOutputShapefileTemp)

    # Loop through that enumeration, calculating each record's raw score
    for nextRecord in enumerationOfRecords:
        newList = []
        for i in list(zScoreList):
            newList.append(nextRecord.getValue(i))
        rawScore = sum(newList)
        nextRecord.setValue(rawField,rawScore)
        enumerationOfRecords.updateRow(nextRecord)

    # Add message
    arcpy.AddMessage("Raw score calculated" + "\n")

    # Delete row and update cursor objects to avoid locking attribute table
    del nextRecord
    del enumerationOfRecords

    rawFieldList = arcpy.ListFields(nameOfOutputShapefileTemp, rawField)

    """ STEP FOUR: DEFINE CLASSIFICATION AND ASSIGN INDEX SCORE """
    """ STEP 4.01: IF USER CHOOSES QUANTILE CLASSIFICATION """
    if classificationMethod == "Quantile":
        arcpy.AddMessage("Calculating index score based on Quantile classification method")

        # Find count of raw score field
        scoreCount = calculate_COUNT_value(nameOfOutputShapefileTemp, rawField)
        arcpy.AddMessage("Count of features is " + str(scoreCount))

        # Divide count into specified number of groups to get the size of each classification group
        # for the quantile classification method
        groupSize = int(scoreCount) / int(classNumber)
        groupSizeInt = int(groupSize) #make group size an integer
        arcpy.AddMessage("Index groups each have " + str(groupSizeInt) + " features in them" + "\n")

        # Create list that that goes from the user specified number of classes to 0
        # (ex. 6 - 0 for 6 classes)
        classNumberList = []
        classNumberList.append(int(classNumber))
        for n in classNumberList:
            classNumberList.append(n - 1)
            if n < 2: break

        # Sort class number list in ascending order
        classNumberList.sort()

        """ STEP 4.02: ASSIGN INDEX SCORE BASED ON QUANTILE CLASSIFICATION """
        # Create index field
        index = ("INDEX_" + yearOfData)
        arcpy.AddField_management(nameOfOutputShapefileTemp, index, "FLOAT", 20, 10)

        arcpy.AddMessage("Assigning index score to each feature" + "\n")

        # Create index assignment list, which will be 1 - whatever the user chose for
        # number of classes
        indexNumberList = []
        for n in classNumberList:
            indexNumberList.append(n + 1) # add 1 to make list 1,2,3 etc instead of 0,1,2
        indexNumberListInter = list(indexNumberList) # make it a list again instead of integers
        indexNumberListShort = indexNumberListInter[:-1] # remove the last item to get correct ending index number

        # Sort table based on rawField
        arcpy.Sort_management(nameOfOutputShapefileTemp, nameOfOutputShapefile, [[rawField, "ASCENDING"]])

        # Assign index numbers for sorted rawField
        # Create an enumeration of updatable records from the shapefile's attribute table
        enumerationOfRecords = arcpy.UpdateCursor(nameOfOutputShapefile)
        # Loop through that enumeration, calculating each record's index score
        b = 0
        m = 0
        for nextRecord in enumerationOfRecords:
            indexScore = indexNumberList[m]
            nextRecord.setValue(index,indexScore)
            b = b + 1
            if b >= groupSizeInt and m <= (len(indexNumberListShort)-1):
                m = m + 1
                b = 0
            if indexScore > (len(indexNumberListShort)):
                indexScore = indexScore - 1
                nextRecord.setValue(index,indexScore)
            enumerationOfRecords.updateRow(nextRecord)
        # Delete row and update cursor objects to avoid locking attribute table
        del nextRecord
        del enumerationOfRecords

        # Delete temporary file
        arcpy.Delete_management(nameOfOutputShapefileTemp)

    """ STEP 4.03: IF USER CHOOSES EQUAL INTERVAL CLASSIFICATION """
    if classificationMethod == "Equal Interval":
        arcpy.AddMessage("Calculating index score based on Equal Interval classification method")

        # Find value range of raw score field
        scoreRange = calculate_range_value(nameOfOutputShapefileTemp, rawField)
        arcpy.AddMessage("The range of raw score values is " + str(scoreRange))

        # Divide range into user specified number of groups to get the size of each
        # classification group for the equal interval classification method
        groupSize2 = scoreRange / float(classNumber)
        arcpy.AddMessage("Index groups each have a value range of " + str(groupSize2))

        # Find minimum value of raw score field
        scoreMin = calculate_MIN_value(nameOfOutputShapefileTemp, rawField)
        arcpy.AddMessage("The minimum value of the raw score field is " + str(scoreMin) + "\n")

        # Create list that that goes from the user specified number of classes to 0
        # (ex. 6 - 0) for 6 classes
        classNumberList = []
        classNumberList.append(int(classNumber))
        for n in classNumberList:
            classNumberList.append(n - 1)
            if n < 2: break

        # Sort class number list in ascending order and modify so that it specifies
        # the correct number of break points (ex. 0 - 4)
        classNumberList.sort()
        classNumberListFinal = classNumberList[0:-2] # number of break points should be one less than number of classes requested

        # Define break point locations for each classification group in list based
        # on the groupSize2 variable
        breakLocationList = []
        for n in classNumberListFinal:
            breakLocationList.append(groupSize2 * (n+1))

        # Define value of variable feature at break point locations in list
        breakValueList = []
        for n in breakLocationList:
            breakValueList.append(scoreMin + n)

        """ STEP 4.04: ASSIGN INDEX SCORE BASED ON EQUAL INTERVAL CLASSIFICATION """
        # Create index field
        index = ("INDEX_" + yearOfData)
        arcpy.AddField_management(nameOfOutputShapefileTemp, index, "FLOAT", 20, 10)

        arcpy.AddMessage("Assigning index score to each feature" + "\n")

        # Create other lists and variables needed for the index assignment process
        classNumberListShort = classNumberListFinal[:-1] # Remove last break point from list
        final = len(classNumberListShort)

        arcpy.Sort_management(nameOfOutputShapefileTemp, nameOfOutputShapefile, [[rawField, "ASCENDING"]])

        # Assign index numbers for sorted rawField
        # Create an enumeration of updatable records from the shapefile's attribute table
        enumerationOfRecords = arcpy.UpdateCursor(nameOfOutputShapefile)
        # Loop through that enumeration, calculating each record's index score
        for nextRecord in enumerationOfRecords:
            for m in classNumberListShort:
                current = classNumberListShort[m]
                next = current + 1
                if nextRecord.getValue(rawField) >= breakValueList[current] and nextRecord.getValue(rawField) < breakValueList[next]:
                    indexScore = next + 1
                    nextRecord.setValue(index,indexScore)
                    enumerationOfRecords.updateRow(nextRecord)
                elif nextRecord.getValue(rawField) < breakValueList[0]:
                    indexScore = 1
                    nextRecord.setValue(index,indexScore)
                    enumerationOfRecords.updateRow(nextRecord)
                elif nextRecord.getValue(rawField) >= breakValueList[final]:
                    indexScore = len(classNumberList)-1
                    nextRecord.setValue(index,indexScore)
                    enumerationOfRecords.updateRow(nextRecord)
                elif m >= len(classNumberListShort): break
        # Delete row and update cursor objects to avoid locking attribute table
        del nextRecord
        del enumerationOfRecords

        # Delete temporary file
        arcpy.Delete_management(nameOfOutputShapefileTemp)

    """ STEP FIVE: DELETE INTERMEDIATE COLUMNS """
    # Delete intermediate columns for each variable in the user-defined variable list
    for variable in varList:
        arcpy.AddMessage("Deleting intermediate columns for: " + variable)

        # Concatenate the list order number to the field name and delete the field called "MEAN"
        meanName = ("MEAN" + str(varList.index(variable)) + str("_" + yearOfData))
        arcpy.DeleteField_management (nameOfOutputShapefile, meanName)

        # Concatenate the list order number to the field name and delete the field called "STDDEV"
        stdDevName = ("STDV" + str(varList.index(variable)) + str("_" + yearOfData))
        arcpy.DeleteField_management (nameOfOutputShapefile, stdDevName)

except Exception as e:
    # If unsuccessful, end gracefully by indicating why
    arcpy.AddError('\n' + "Script failed because: \t\t" + e.message )
    # ... and where
    exceptionreport = sys.exc_info()[2]
    fullermessage   = traceback.format_tb(exceptionreport)[0]
    arcpy.AddError("at this location: \n\n" + fullermessage + "\n")
