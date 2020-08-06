import math
import re

def GenerateAbbrs(abbreviationFileName, indices):
    """
    Get a list of state/Territory names to abbreviations
    Returns a dictionary ordered by location name
    """
    Rn=indices[2][0]
    Rp=indices[2][1]
    Sn=indices[2][2]
    Sp=indices[2][3]

    Ri=max(Rn,Rp)
    Si=max(Sn,Sp)

    try:
        with open(abbreviationFileName) as f:
            abbr={}
            subAbbr={}
            for line in f:
                strs=line.split(",")
                if len(strs)>Ri:
                    abbr[strs[Rn].strip()]=strs[Rp].strip()
                if len(strs)>Si:
                    subAbbr[strs[Sn].strip()]=strs[Sp].strip()
            
            f.close()
        return abbr,subAbbr
    except:
        return {},{}

def GenerateIndices(indicesFileName):
    """
    Get a list of state/Territory names to abbreviations
    Returns a dictionary ordered by location name
    """
    
    ret=[[0,1,2,3],[0,1,2,3],[0,1,2,3],[0,1,2,3]]
    lineCount=0
    try:
        with open(indicesFileName) as f:
            for line in f:
                try:
                    strs=line.split(",")
                    ret[lineCount]=[GetIndex(strs[0]),GetIndex(strs[1]),GetIndex(strs[2]),GetIndex(strs[3])]
                except:
                    pdb.gimp_message("index getter exception on line = "+str(lineCount))
                    
                lineCount+=1
            f.close()
    except:
        try:
            f.close()
        except:
            pdb.gimp_message("index getter exception OUTER")
            
        
    return ret

def GetIndex(val):
    try:
        return int(val)-1
    except:
        try:
            ret=0
            val=val.upper().strip()
            base=ord('A')-1
            for c in val:
                ret*=26
                ret+=ord(c)-base
            return ret-1
        except:
            pdb.gimp_message("could not turn value to index = "+str(val))
            return 0


def StripLocList(CountyNameToCoordinatesFileName,abbr,subAbbr,indices):
    """
    Open the original county location list and create a Dict keyed to "StateAbbr CountyName" with tuples
    holding lat, long
    """
    iReg=indices[0][0]
    iSub=indices[0][1]
    iLat=indices[0][2]
    iLon=indices[0][3]
    #pdb.gimp_message("index = "+str(indices[0]))

    ret={}
    with open(CountyNameToCoordinatesFileName) as f:
        for line in f:
            try:
                strs=line.split(",")
                fromSt=strs[iReg].strip()
                fromCt=strs[iSub].strip()
                if fromSt in abbr:
                    fromSt=abbr[fromSt]
                if fromCt in subAbbr:
                    fromCt=subAbbr
                Lat=float(strs[iLat].strip().strip("\""))
                Long=float(strs[iLon].strip().strip("\""))

                ret[fromSt+" "+fromCt]=(Lat,Long)

            except:
                pdb.gimp_message("could not parse = "+line+" for indices "+str(indices[0]))
        f.close()

    return ret


def StripMobList(countyMobilityFileName,abbreviationFileName,includeRegex,abbr,subAbbr, indices):
    """
    Go through the mobility list and combine all counties which move
    into the state

    return a Dict keyed to "StateAbbr CountyName" with outbound flow from the state
    """
    iReg=indices[1][0]
    iSub=indices[1][1]
    iVal=indices[1][2]

    #pdb.gimp_message("val index = "+str(iVal))

    Region=re.compile(".*")
    SubRegion=re.compile(".*")
    regexTokens=includeRegex.split("@")
    if len(regexTokens)>0:
        Region=re.compile(regexTokens[0])
    if len(regexTokens)>1:
        SubRegion=re.compile(regexTokens[1])
    

    ret={}

    with open(countyMobilityFileName) as f:
        for line in f:
            try:
                strs=getStrings(line)#line.split(",")

                fromSt=strs[iReg].strip()
                fromCt=strs[iSub].strip()
                if Region.match(fromSt) and SubRegion.match(fromCt):
                    flowStr=strs[iVal].strip().strip("\"") #handle numbers inputted as strings (for values >= 1,000)
                    flow=float(flowStr)
                    if fromSt in abbr:
                        fromSt=abbr[fromSt]
                    if fromCt in subAbbr:
                        fromCt=subAbbr
                    if flow!=0:
                        key=fromSt+" "+fromCt
                        if key in ret:
                            ret[key]+=flow
                        else:
                            ret[key]=flow
                    
            except:
                pdb.gimp_message("could not parse = "+line+" for indices "+str(indices[0]))

        f.close()

    return ret


def getStrings(line):
    ret=[]
    strs=line.split(",")
    substring=""
    for s in strs:
        if substring == "":
            if "\"" in s:
                substring=s.strip("\"")
            else:
                ret.append(s)
        else:
            if "\"" in s:
                ret.append(substring+s.strip("\""))
                substring=""
            else:
                substring = substring + s
    return ret
    # return strs
                

def GenerateAnchorPoints(anchorFileName, indices,margin,scalePkg):
    iName=indices[3][0]
    iLat=indices[3][1]
    iLon=indices[3][2]

    try:
        locList={}
        with open(anchorFileName) as f:
            for line in f:
                try:
                    strs=line.split(",")
                    name=strs[iName].strip()
                    Lat=float(strs[iLat].strip().strip("\""))
                    Long=float(strs[iLon].strip().strip("\""))

                    locList[name]=(Lat,Long)
                except:
                    pass
            f.close()

        locList=convertCoordinatesToMercator(locList)

        dummyFlow ={}
        for key,value in locList.items():
            Lat,Long=value
            dummyFlow[key]=(0,Lat,Long)
        
        return coordinatePercentages([dummyFlow],margin,scalePkg)[0][0]

    except:
        pass

    return {}


def CreatePartitionedGeoData(minDist,mobList,locList,margin,combine=True):
    """
    create a list of dictionaries of geodata keyed to "StateAbbr County" eg(UT Davis County)
    which contains a tuple of flow, lat, long
    each dictionary will never contain two points less than minDist apart

    if combine = True then only one dictionary will be created but counties less than minDist apart
    will have their flow rates combined
    """

    useTree=False #might be faster on really large datasets, but seems kind of slow for what I'm doing

    locList=convertCoordinatesToMercator(locList)

    DataTree= []
    UnLocatedData=[]

    for key in mobList:
        Flow=mobList[key]
        if key in locList:
            Lat, Long=locList[key]
            PartitionGeoData(key,Flow,Lat,Long,DataTree,minDist,combine)
        else:
            UnLocatedData.append((key,Flow))

    if useTree:
        PartitionedData=stripTree(DataTree)
    else:
        PartitionedData=DataTree

    PartitionedData,pkg=coordinatePercentages(PartitionedData,margin)

    

    return PartitionedData, UnLocatedData ,pkg

def convertCoordinatesToMercator(Dict):
    """
    Convert Lat Long to the mercator projection so that it can
    be more easily combined with maps
    """
    retDict={}
    for key, val in Dict.items():
        Lat,Long=val
        (mLat,mLong)=mercatorConversion((Lat,Long))
        retDict[key]=(mLat,mLong)

    return retDict


def zeroCorrdinates(dataDictList,margin, scalePkg=None):
    """
    make all coordinates relative to zero.
    The lowest coordinates become margin and all cordinates are
    changed to be relative to those.

    All dictionaries occupy the same dimensions, the smallest coordinate on one
    dictionary is the smallest coordinate on all dictionaries

    returns a new list of dictionaries
    """
    
    minLat=float("inf")
    minLong=float("inf")

    retDictList=[]

    if scalePkg==None:
        for Dict in dataDictList:
            for key in Dict:
                Flow,Lat,Long=Dict[key]
                if Lat<minLat:
                    minLat=Lat
                if Long<minLong:
                    minLong=Long
    else:
        minLat,maxLat,minLong,maxLong=scalePkg

    
    for Dict in dataDictList:
        newDict={}
        retDictList.append(newDict)
        for key in Dict:
            Flow,Lat,Long=Dict[key]
            newDict[key]=(Flow,Lat-minLat+margin,Long-minLong+margin)

    return retDictList, (minLat,float("-inf"),minLong,float("-inf"))

def coordinatePercentages(dataDictList,margin, scalePkg=None, preserveAspect=True):
    """
    make all coordinates percentages
    smallest coordinates will be closer to 0, larger cordinates will be closer to 1
    margin specifies how far from zero and one the smallest and largest coordinates will be
    (relative to coordinate space, not percentage)

    All dictionaries occupy the same dimensions, the smallest coordinate on one
    dictionary is the smallest coordinate on all dictionaries

    returns a new list of dictionaries
    """
    

    zeroed, zPkg=zeroCorrdinates(dataDictList,margin,scalePkg)
    minLat,maxLat,minLong,maxLong=zPkg
    retDictList=[]

    if scalePkg==None:
        for Dict in zeroed:
            for key in Dict:
                Flow,Lat,Long=Dict[key]
                if Lat>maxLat:
                    maxLat=Lat
                if Long>maxLong:
                    maxLong=Long
        maxLong+=margin
        maxLat+=margin

    else:
        nminLat,maxLat,nminLong,maxLong=scalePkg

    if preserveAspect:
        maxLong=max(maxLong,maxLat)
        maxLat=maxLong
    
    for Dict in zeroed:
        newDict={}
        retDictList.append(newDict)
        for key in Dict:
            Flow,Lat,Long=Dict[key]
            newDict[key]=(Flow,Lat/maxLat,Long/maxLong)

    return retDictList,(minLat,maxLat,minLong,maxLong)
        



def PartitionGeoData(iKey,iFlow,iLat,iLong,dataDictList,minDist,combine=False):
    """
    add a new element to a list of dictionaries which is no less than
    min dist apart from any other element on its respective dictionary

    if combine=True instead of creating new dictionaries for close items
    they will simply have their flows combined

    returns a list of dictionaries
    """
    for Dict in dataDictList:
        room=True
        for key in Dict:
            Flow,dLat,dLong=Dict[key]
            if dist((iLat,iLong),(dLat,dLong))<minDist:
                if combine:
                    Dict[key]=(Flow+iFlow,dLat,dLong)
                    return
                else:
                    room=False
                    break
        if room:
            Dict[iKey]=(iFlow,iLat,iLong)
            return
        
    dataDictList.append({iKey:(iFlow,iLat,iLong)})


def PartitionGeoDataTree(iKey,iFlow,iLat,iLong,treeList,minDist,combine=False):
    """
    add a new element to a list of trees which is no less than
    min dist apart from any other element on its respective dictionary

    if combine=True instead of creating new dictionaries for close items
    they will simply have their flows combined

    returns a list of dictionaries
    """

    room=True
    for tree,Dict in treeList:
        #get closest point in tree to iLat, iLong
        pdist,point = get_nearest(tree,(iLat,iLong),2,dist)

        if pdist<minDist:
            #if no room, combine if that is perferred
            # otherwise loop to the next tree
            if combine:
                point.flow+=iFlow
                Dict[point.key]=(point.flow+iFlow,point[0],point[1])
                return
        else:
            #if room, add the point to the tree
            newPoint=PointContainer([iLat,iLong])
            newPoint.flow=iFlow
            newPoint.key=iKey
            add_point(tree,newPoint,2)
            Dict[iKey]=(iFlow,iLat,iLong)
            return

    newPoint=PointContainer([iLat,iLong])
    newPoint.flow=iFlow
    newPoint.key=iKey
    treeList.append((make_kd_tree([newPoint], 2),{iKey:(iFlow,iLat,iLong)}))

def stripTree(treeList):
    retDictList=[]
    for tree,Dict in treeList:
        retDictList.append(Dict)
    return retDictList

def dist (a, b):
    """
    simple euclidian distance
    """
    return math.sqrt((a[0]-b[0])**2+(a[1]-b[1])**2)

def mercatorConversion(latLong):
    """
    take latlong as a tuple and return a new "latlong" tuple which is adjusted
    for the mercator projection.

    Modified From Jos Vazquez at: https://gis.stackexchange.com/questions/156035/calculating-mercator-coordinates-from-lat-lon
    """
    Lat, Long= latLong
    r_major = 6378137.000
    x = r_major * math.radians(Long)
    scale = x/Long
    y = 180.0/math.pi * math.log(math.tan(math.pi/4.0 + Lat * (math.pi/180.0)/2.0)) * scale
    return (y, x)

def getDistortion(img, layer):
    yDiff=0

    dWidth=pdb.gimp_drawable_width(layer)
    dHeight=pdb.gimp_drawable_height(layer)
    iWidth = float(pdb.gimp_image_width(img))
    iHeight = float(pdb.gimp_image_height(img))

    center=dWidth/2
    #start from the top center and work down to the first non
    # transparent pixel
    for y in range(dHeight):
        c,p = pdb.gimp_drawable_get_pixel(layer,center,y)
        if c<4:
            #pdb.gimp_message("num_components less than 4= "+str(c))
            xS= dWidth/iWidth #the x transform factor
            xL= dWidth #how many y pixels are traveled to achieve the above reduction
            xW= iWidth
            if dHeight>iHeight:
                Y=1
            else:
                Y=dHeight/iHeight
            
            #pdb.gimp_message("iWidth= "+str(iWidth))
            #pdb.gimp_message("iHeight= "+str(iHeight))
            #pdb.gimp_message("dWidth= "+str(dWidth))
            #pdb.gimp_message("dHeight= "+str(dHeight))
            #pdb.gimp_message("xFactor= "+str(getXFactor(xS,xL,xW)))
            #pdb.gimp_message("yFactor= "+str(Y))
            return Y,(getXFactor(xS,xL,xW),xW)
        if p[3]>0:
            break
        yDiff+=1
    
    xDiff=0
    for x in range(center):
        c,p = pdb.gimp_drawable_get_pixel(layer,x,yDiff)
        if p[3]>0:
            break
        xDiff+=1
    
    yFactor= (dHeight-yDiff)/iHeight
    xS= (dWidth-xDiff)/iWidth #the x transform factor
    xL= dHeight-yDiff #how many y pixels are traveled to achieve the above reduction
    xW= iWidth

    #pdb.gimp_message("iWidth= "+str(iWidth))
    #pdb.gimp_message("iHeight= "+str(iHeight))
    #pdb.gimp_message("dWidth= "+str(dWidth-xDiff))
    #pdb.gimp_message("dHeight= "+str(dHeight-yDiff))
    #pdb.gimp_message("xFactor= "+str(getXFactor(xS,xL,xW)))
    #pdb.gimp_message("yFactor= "+str(yFactor))

    return (yFactor,(getXFactor(xS,xL,xW),xW))

def getXFactor(xS,xL,xW):
    return -(xW-(xW*xS))/xL

def getXScale(x,y,xPacket):
    xF,xW=xPacket
    widthAtY=xF*y+xW
    return widthAtY/xW

    
def getTextPkg(mimmcText):
    fontSize=20
    fontSizeUnit=0
    justification=0
    kerning=0
    fontFace="Sans"
    fontColor=(0,0,0,255)
    letterSpacing=0
    hinting=0
    autohint=0


    if mimmcText and pdb.gimp_drawable_is_text_layer(mimmcText):
        fontSize, fontSizeUnit = pdb.gimp_text_layer_get_font_size(mimmcText)
        justification = pdb.gimp_text_layer_get_justification(mimmcText)
        kerning = pdb.gimp_text_layer_get_kerning(mimmcText)
        spacing = pdb.gimp_text_layer_get_letter_spacing(mimmcText)
        fontFace=pdb.gimp_text_layer_get_font(mimmcText)
        fontColor=pdb.gimp_text_layer_get_color(mimmcText)
        letterSpacing=pdb.gimp_text_layer_get_letter_spacing(mimmcText)
        hinting, autohint=pdb.gimp_text_layer_get_hinting(mimmcText)
    
    return (fontSize,fontSizeUnit,justification,kerning,fontFace,fontColor,letterSpacing,hinting,autohint)


def plugin_main(timg, tdrawable,
locations,values,includeRegex,abbr,keyPoints,indices,
mimmicDistortion,scaleHeightWithDepth,scaleWidthWithDepth,
minDist,
mimmcText,topN,
meterMaxVal,meterHeight,meterWidth,minWidth,meterMargin,
borderOpacity,borderColor):



    maxColor=pdb.gimp_context_get_foreground()
    minColor=pdb.gimp_context_get_background()

    R,G,B,A=borderColor
    if borderOpacity<=1:
        borderOpacity*=255
    if R<=1 and G<=1 and B<=1:
        R*=255
        G*=255
        B*=255
    borderColor=(R,G,B,borderOpacity)
    cellShade=borderOpacity>0

    doText= (topN == -1)
    doMeter=meterHeight>0

    verticalReduction, xPacket = getDistortion(timg,mimmicDistortion)

    combineNearbyPoints=True #probably best to leave this on for sorting values from front to back, if you want less points combined, lower minDist


    pdb.gimp_progress_init("get locations",None)
    errors= set()

    width = pdb.gimp_image_width(timg)
    height = pdb.gimp_image_height(timg)

    img = gimp.Image(width, height, RGB)

    margin=5

    textPkg=getTextPkg(mimmcText)


    perserveAspect=True

    countyMobilityFileName=values
    abbreviationFileName=abbr
    CountyNameToCoordinatesFileName=locations
    indicesFileName=indices
    anchorFileName=keyPoints


    indices=GenerateIndices(indicesFileName)


    abbr,subAbbr=GenerateAbbrs(abbreviationFileName,indices)
    locList=StripLocList(CountyNameToCoordinatesFileName,abbr,subAbbr,indices)

    pdb.gimp_progress_update(.02)
    pdb.gimp_progress_set_text("get values")
    pdb.gimp_progress_pulse()
    valList=StripMobList(countyMobilityFileName,abbreviationFileName,includeRegex,abbr,subAbbr,indices)

    pdb.gimp_progress_update(.05)
    pdb.gimp_progress_set_text("group data points")
    pdb.gimp_progress_pulse()
    migrations,unlocatedData,scalePkg=CreatePartitionedGeoData(minDist, valList,locList,margin,combineNearbyPoints)
    sortedMigrations=sortDataBy(migrations,lambda x: -x[1][1])
    topValueMigrations=sortDataBy(migrations,lambda x: -x[1][0])

    anchors=GenerateAnchorPoints(anchorFileName,indices,margin,scalePkg)
    
    pdb.gimp_progress_update(.1)
    pdb.gimp_progress_set_text("drawing data")
    pdb.gimp_progress_pulse()

    Lwidth=width
    Lheight=height
    if perserveAspect:
        Lheight=min(Lheight,Lwidth)
        Lwidth=Lheight


    if meterMaxVal == 0:
        meterMaxVal=float("-inf")
        for Dict in migrations:
            for key in Dict:
                meterMaxVal=max(meterMaxVal,Dict[key][0])


    totalPoints=0
    for Dict in migrations:
        totalPoints+=len(Dict)
    points=0.0
    
    allPoints=totalPoints+len(unlocatedData)
    
    DataGroup=pdb.gimp_layer_group_new(img)
    pdb.gimp_layer_set_name(DataGroup,str(allPoints)+" Data Points")
    pdb.gimp_image_insert_layer(img, DataGroup, None, 0)

    

    legendGroup=pdb.gimp_layer_group_new(img)
    pdb.gimp_layer_set_name(legendGroup,"Legend")
    pdb.gimp_image_insert_layer(img, legendGroup, DataGroup, 0)
    drawMeter(img,Lwidth/2,Lheight/2,"Scale Meter",meterMaxVal,meterMargin,meterWidth,minWidth,meterHeight,meterMaxVal,1,1,False,False,maxColor,minColor,cellShade,borderColor)
    drawText(img,Lwidth/2,Lheight/2,"MinLabel",0,textPkg)
    gHeight=1
    if scaleHeightWithDepth:
        gHeight=int(meterHeight*verticalReduction)
    else:
        gHeight=int(meterHeight)
    drawText(img,Lwidth/2,Lheight/2-gHeight,"MaxLabel",meterMaxVal,textPkg)

    MainDrawProgress=.9
    if topN>0:
        MainDrawProgress-=.3
    if len(anchors)>0:
        MainDrawProgress-=.1

    count=0
    locatedDataGroup=pdb.gimp_layer_group_new(img)
    pdb.gimp_layer_set_name(locatedDataGroup,"Positioned Data "+str(totalPoints)+" points")
    pdb.gimp_image_insert_layer(img, locatedDataGroup, DataGroup, 0)
    for subList in sortedMigrations:
        pdb.gimp_progress_pulse()
        count+=1

        DictGroup=pdb.gimp_layer_group_new(img)
        pdb.gimp_layer_set_name(DictGroup,"Values "+str(count))
        pdb.gimp_image_insert_layer(img, DictGroup, locatedDataGroup, 0)

        for item in subList:
            pdb.gimp_progress_update(.1+MainDrawProgress*(points/allPoints))
            points+=1
            
            (key,(Flow,Lat,Long))=item

            pointGroup=pdb.gimp_layer_group_new(img)
            pdb.gimp_layer_set_name(pointGroup,str(Flow)+" near "+key)
            pdb.gimp_image_insert_layer(img, pointGroup, DictGroup, 0)

            x=Long*Lwidth
            Lat=Lat*Lheight
            y=Lheight-Lat

            horizontalReduction= getXScale(x,Lat*verticalReduction,xPacket)

            x=centerHorizontalReduction(x,horizontalReduction,Lwidth)
            y*=verticalReduction


            if doMeter:
                drawMeter(img,x,y,"meter near "+key,Flow,meterMargin,meterWidth,minWidth,meterHeight,meterMaxVal,verticalReduction,horizontalReduction,scaleHeightWithDepth,scaleWidthWithDepth,maxColor,minColor,cellShade,borderColor)
                pdb.gimp_progress_set_text("drawing data")

            if doText:
                valString=str(Flow).strip("0").strip(".")
                drawText(img,x,y,valString+" "+key,valString,textPkg)



    unLocatedGroup=pdb.gimp_layer_group_new(img)
    pdb.gimp_layer_set_name(unLocatedGroup,"Data without position "+str(len(unlocatedData))+" points")
    pdb.gimp_image_insert_layer(img, unLocatedGroup, DataGroup, 0)
    for key, Flow in unlocatedData:
        #pdb.gimp_message("unpositioned"+key)

        pdb.gimp_progress_update(.1+MainDrawProgress*(points/allPoints))
        points+=1
        
        pointGroup=pdb.gimp_layer_group_new(img)
        pdb.gimp_layer_set_name(pointGroup,str(Flow)+" near "+key)
        pdb.gimp_image_insert_layer(img, pointGroup, unLocatedGroup, 0)

        x=Lwidth/2
        y=Lheight/2

        if doMeter:
            drawMeter(img,x,y,"meter near "+key,Flow,meterMargin,meterWidth,minWidth,meterHeight,meterMaxVal,1,1,False,False,maxColor,minColor,cellShade,borderColor)
            pdb.gimp_progress_set_text("drawing unlocated data")

        if doText or topN>0:
            valString=str(Flow).strip("0").strip(".")
            drawText(img,x,y,valString+" "+key,valString,textPkg)





    if topN>0:
        pdb.gimp_progress_set_text("drawing top "+str(topN)+" labels")
        meterProgress=.9-MainDrawProgress
        meterBase=.1+MainDrawProgress
        points=0.0
        topNgroup=pdb.gimp_layer_group_new(img)
        pdb.gimp_layer_set_name(topNgroup,"highest "+str(topN)+" point labels")
        pdb.gimp_image_insert_layer(img, topNgroup, DataGroup, 0)
        for subList in topValueMigrations:
            pdb.gimp_progress_pulse()
            count+=1

            textGroup=pdb.gimp_layer_group_new(img)
            pdb.gimp_layer_set_name(textGroup,"Values "+str(count))
            pdb.gimp_image_insert_layer(img, textGroup, topNgroup, 0)

            for item in subList:
                if points>topN:
                    break
                pdb.gimp_progress_update(meterBase+meterProgress*(points/topN))
                points+=1
                (key,(Flow,Lat,Long))=item
                pointGroup=pdb.gimp_layer_group_new(img)
                pdb.gimp_layer_set_name(pointGroup,str(Flow)+" near "+key)
                pdb.gimp_image_insert_layer(img, pointGroup, textGroup, 0)
                x=Long*Lwidth
                Lat=Lat*Lheight
                y=Lheight-Lat
                horizontalReduction= getXScale(x,Lat*verticalReduction,xPacket)
                x=centerHorizontalReduction(x,horizontalReduction,Lwidth)
                y*=verticalReduction

                valString=str(Flow).strip("0").strip(".")
                drawText(img,x,y,valString+" "+key,valString,textPkg)


    pdb.gimp_progress_set_text("drawing anchors")
    totalPoints=len(anchors)
    points=0.0
    anchorGroup=pdb.gimp_layer_group_new(img)
    pdb.gimp_layer_set_name(anchorGroup,"anchors")
    pdb.gimp_image_insert_layer(img, anchorGroup, DataGroup, 0)
    for key,value in anchors.items():
        pdb.gimp_progress_update(.9+.1*(points/totalPoints))
        points+=1
        Flow,Lat,Long=value
        x=Long*Lwidth
        Lat=Lat*Lheight
        y=Lheight-Lat
        horizontalReduction= getXScale(x,Lat*verticalReduction,xPacket)
        x=centerHorizontalReduction(x,horizontalReduction,Lwidth)
        y*=verticalReduction
        drawMeter(img,x,y,"Anchor: "+key,meterMaxVal,meterMargin,meterWidth,minWidth,meterHeight,meterMaxVal,1,1,False,False,inv(maxColor),inv(minColor),cellShade,borderColor)
        pdb.gimp_progress_set_text("drawing anchors")

    pdb.gimp_progress_end()
    gimp.Display(img) 

def inv(c):
    """invert color"""
    if len(c)==3:
        R,G,B=c
        if R<=1 and G<=1 and B<=1:
            return (255*(1-R),255*(1-G),255*(1-B))
        else:
            return(255- R,255-G,255-B)
    if len(c)==4:
        R,G,B,A=c
        if R<=1 and G<=1 and B<=1:
            return (255*(1-R),255*(1-G),255*(1-B),A)
        else:
            return(255- R,255-G,255-B,A)
    return c


def drawText(img,x,y,name,valString,textPkg):
    (fontSize,fontSizeUnit,justification,kerning,fontFace,fontColor,letterSpacing,hinting,autohint)=textPkg
    textLayer=pdb.gimp_text_layer_new(img,valString,fontFace,fontSize,fontSizeUnit)
    img.add_layer(textLayer)

    pdb.gimp_text_layer_set_color(textLayer,fontColor)
    pdb.gimp_text_layer_set_justification(textLayer,justification)
    pdb.gimp_text_layer_set_kerning(textLayer,kerning)
    pdb.gimp_text_layer_set_letter_spacing(textLayer,letterSpacing)
    pdb.gimp_text_layer_set_hinting(textLayer,hinting,autohint)

    pdb.gimp_layer_set_offsets(textLayer,x,y-pdb.gimp_drawable_height(textLayer))
    pdb.gimp_layer_set_name(textLayer,name)


def drawMeter(img,x,y,name,Flow,meterMargin,meterWidth,minWidth,meterHeight,meterMaxVal,verticalReduction,horizontalReduction,scaleHeightWithDepth,scaleWidthWithDepth,maxColor,minColor,cellShade,borderColor):
    heightPercentage=float(Flow)/meterMaxVal
    gHeight=1
    if scaleHeightWithDepth:
        gHeight=int(meterHeight*heightPercentage*verticalReduction)
    else:
        gHeight=int(meterHeight*heightPercentage)
    if gHeight<1:
        gHeight=1

    gWidth=1
    if scaleWidthWithDepth:
        gWidth=int(meterWidth*heightPercentage*horizontalReduction)
    else:
        gWidth=int(meterWidth*heightPercentage)
    if gWidth<minWidth:
        gWidth=minWidth
    
    halfWidth=gWidth/2.0
    gWidth+=meterMargin*2
    gHeight+=meterMargin*2

    gradientLayer = pdb.gimp_layer_new(img, gWidth, gHeight,RGBA_IMAGE, name, 100, NORMAL_MODE)
    img.add_layer(gradientLayer)

    loColor=minColor
    hiColor=lerp(loColor,maxColor,heightPercentage)
    for yy in range(meterMargin,gHeight-meterMargin):
        color=lerp(loColor,hiColor,float(gHeight-yy)/gHeight)
        wl=getWidthAt(halfWidth,yy,gHeight)+meterMargin
        wh=gWidth-wl
        for xx in range(wl,wh):
            pdb.gimp_drawable_set_pixel(gradientLayer,xx,yy,4,color)
    
    if cellShade:
        for yy in range(meterMargin,gHeight-meterMargin):
            wl=getWidthAt(halfWidth,yy,gHeight)+meterMargin
            wh=gWidth-wl
            pdb.gimp_drawable_set_pixel(gradientLayer,wl,yy,4,borderColor)
            pdb.gimp_drawable_set_pixel(gradientLayer,wh-1,yy,4,borderColor)

    if meterMargin>0:
        pdb.plug_in_gauss_rle2(img,gradientLayer,0,min(meterMargin,gHeight-meterMargin*2))

    pdb.gimp_layer_set_offsets(gradientLayer,x-gWidth/2,y-gHeight)

def lerp(valA, valB, t):
    if t>1:
        return valB
    if t<0:
        return valA
    return [lerp1(valA[i],valB[i],t) for i in range(0,len(valA))]

def lerp1(valA,valB,t):
    return valA+t*(valB-valA)

def getWidthAt(maxWidth,atHeight,maxHeight):
    return int(maxWidth*(1-(atHeight/float(maxHeight))**2))

def centerHorizontalReduction(x,reductionFactor,width):
    width/=2
    if x > width:
        x-=width
        return width+x*reductionFactor
    if x < width:
        x=width-x
        return width-x*reductionFactor



def sortDataBy(dictList,sortMethod):
    retList=[]
    for Dict in dictList:
        newList=[]
        for key,value in Dict.items():
            newList.append((key,value))
        retList.append(sorted(newList,key=sortMethod))
    return retList

# https://github.com/Vectorized/Python-KD-Tree/blob/master/kdtree.py
def make_kd_tree(points, dim, i=0):
    if len(points) > 1:
        points.sort(key=lambda x: x[i])
        i = (i + 1) % dim
        half = len(points) >> 1
        return [
            make_kd_tree(points[: half], dim, i),
            make_kd_tree(points[half + 1:], dim, i),
            points[half]
        ]
    elif len(points) == 1:
        return [None, None, points[0]]

# Adds a point to the kd-tree
def add_point(kd_node, point, dim, i=0):
    if kd_node is not None:
        dx = kd_node[2][i] - point[i]
        i = (i + 1) % dim
        for j, c in ((0, dx >= 0), (1, dx < 0)):
            if c and kd_node[j] is None:
                kd_node[j] = [None, None, point]
            elif c:
                add_point(kd_node[j], point, dim, i)

# k nearest neighbors
def get_knn(kd_node, point, k, dim, dist_func, return_distances=True, i=0, heap=None):
    import heapq
    is_root = not heap
    if is_root:
        heap = []
    if kd_node is not None:
        dist = dist_func(point, kd_node[2])
        dx = kd_node[2][i] - point[i]
        if len(heap) < k:
            heapq.heappush(heap, (-dist, kd_node[2]))
        elif dist < -heap[0][0]:
            heapq.heappushpop(heap, (-dist, kd_node[2]))
        i = (i + 1) % dim
        # Goes into the left branch, and then the right branch if needed
        for b in [dx < 0] + [dx >= 0] * (dx * dx < -heap[0][0]):
            get_knn(kd_node[b], point, k, dim, dist_func, return_distances, i, heap)
    if is_root:
        neighbors = sorted((-h[0], h[1]) for h in heap)
        return neighbors if return_distances else [n[1] for n in neighbors]

# For the closest neighbor
def get_nearest(kd_node, point, dim, dist_func, return_distances=True, i=0, best=None):
    if kd_node is not None:
        dist = dist_func(point, kd_node[2])
        dx = kd_node[2][i] - point[i]
        if not best:
            best = [dist, kd_node[2]]
        elif dist < best[0]:
            best[0], best[1] = dist, kd_node[2]
        i = (i + 1) % dim
        # Goes into the left branch, and then the right branch if needed
        for b in [dx < 0] + [dx >= 0] * (dx * dx < best[0]):
            get_nearest(kd_node[b], point, dim, dist_func, return_distances, i, best)
    return best if return_distances else best[1]

class PointContainer(list):
    def __new__(self, value, name = None, values = None):
        s = super(PointContainer, self).__new__(self, value)
        return s


def Test():
    countyMobilityFileName='countymobility.csv'
    abbreviationFileName="abbr.csv"
    CountyNameToCoordinatesFileName="cntyLcOrig.csv"
    minDist=5
    
    countyMobilityFileName='countymobility.csv'
    abbreviationFileName="abbr.csv"
    CountyNameToCoordinatesFileName="cntyLcOrig.csv"
    indicesFileName="indices.csv"

    indices=GenerateIndices(indicesFileName)

    includeRegex="^(Utah.+|(?!Utah).*)$@.*"

    errors= set()
    abbr,subAbbr=GenerateAbbrs(abbreviationFileName,indices)
    locList=StripLocList(CountyNameToCoordinatesFileName,abbr,subAbbr,indices)

    valList=StripMobList(countyMobilityFileName,abbreviationFileName,includeRegex,abbr,subAbbr,indices)

    migrations,unlocatedData, scalePkg=CreatePartitionedGeoData(minDist, valList,locList,5,True)

    for Dict in migrations:
        for key,value in Dict.items:
            Flow,Lat,Long=value
            i=int(flow)
            i=int(Lat)
            i=int(Long)


try:
    # if running from gimp, this should work and the script is treated as a plugin
    from gimpfu import *
except:
    #if running from command line, only test data processing functions
    print("Test Mode")
    import sys
    Test()
    sys.exit()

register(
        "Geolocation_Data_Plotter",
        "Plot Values on a Mercator Projection Map",
        "Use between 2 - 4 comma separated value sheets to plot data on a map. The first must have the columns \
            Region (like a state), SubRegion (like a county), Lat, Long. This tells us where to draw data, The second \
            must have the columns Region, SubRegion, Value. The Third isn't required, it can swap out names on one sheet for \
            names on another (for example, if one sheet was made with state names and the other was made with abbreviations. \
            It must have the columns Region name, perferred region name. Optionally the third and fourth columns can be \
            Subregion name, perferred subregion name. The last sheet is also optional. It can contain a few known allignment \
            points. It must have the collumns Allignment point name, lat, long. This file can help you scale an imported map \
            asset.",
        "Daniel Williams",
        "Daniel Williams",
        "2020",
        "<Image>/Filters/Render/Data Points",
        "RGB*",
        [
                (PF_FILE, "locations", "Region,Subregion,Lat,Long CSV", None),
                (PF_FILE, "values", "Region,Subregion,Value CSV", None),
                (PF_STRING, "onlySeeValue", "         Include Region@Subregion regex", ".*@.*"),
                (PF_FILE, "abbr", "(Optional) Region,Perferred Name,Subregion,Perferred Name CSV", None),
                (PF_FILE, "keyPoints", "(Optional) Alignment Point Name,Lat,Long CSV", None),
                (PF_FILE, "indices", "(Optional) Alternate Indices for above files CSV", None),
                (PF_DRAWABLE, "distort", "- Mimmic Distortion", None),
                (PF_BOOL, "scaleHeight", "         Distort data height", FALSE),
                (PF_BOOL, "scaleWidth", "         Distort data width", FALSE),
                (PF_FLOAT, "min_dist", "- Minimum Distance before points are combined", 350000),
                (PF_DRAWABLE, "text", "- (Optional) Mimmic Text", None),
                (PF_INT, "topResults", "         Display text for top N data points (-1 = All)", -1),
                (PF_INT, "maxMeterHeight", "- Value of scale meter (0 = Auto)", 0),
                (PF_INT, "meterHeight", "         Pixel height of biggest meter (0 = Off)", 100),
                (PF_INT, "meterWidth", "         Pixel width of biggest meter", 30),
                (PF_INT, "meterMinWidth", "         Pixel width of smallest meter", 5),
                (PF_INT, "meterMargin", "         Meter blur (0 = Off)", 10),
                (PF_FLOAT, "borderOpacity", "         Border Opacity (0 = Off)", 255),
                (PF_COLOR, "borderColor", "         Border color", (0,0,0)),
        ],
        [],
        plugin_main)
 
main()








