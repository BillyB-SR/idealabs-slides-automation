function extractPresentationDataAsJson(startSlide, endSlide) {
    // ---- CONFIGURATION OPTIONS ----
    var INCLUDE_IMAGE_POSITION = false;  // false => do not show .position in final JSON
    var INCLUDE_IMAGE_SIZE     = false;  // false => do not show .size in final JSON
    
    // If two images' Y positions differ by <= this threshold, treat them as on the same "row".
    var Y_POSITION_THRESHOLD = 10;
    
    // Background image detection thresholds
    var BG_POSITION_THRESHOLD = 15;  // px away from (0,0)
    var BG_SIZE_THRESHOLD     = 50;  // px difference from 720x405
    var BG_WIDTH  = 720;            // typical background width
    var BG_HEIGHT = 405;            // typical background height
    
    // ---- MAIN CODE ----
    
    var presentation = SlidesApp.getActivePresentation();
    var slides = presentation.getSlides();
    
    // Determine slide range
    var totalSlides = slides.length;
    var firstSlide = (startSlide && startSlide > 0) ? startSlide : 1;
    var lastSlide  = (endSlide && endSlide <= totalSlides) ? endSlide : 12;
    if (firstSlide > lastSlide) {
      var temp = firstSlide;
      firstSlide = lastSlide;
      lastSlide = temp;
    }
    if (firstSlide < 1) firstSlide = 1;
    if (lastSlide > totalSlides) lastSlide = totalSlides;
    
    var data = { slides: [] };
    
    /**
     * Check if an image is near (0,0) and near 720x405 => "background"
     */
    function isBackgroundImage(left, top, width, height) {
      var nearLeft   = Math.abs(left)   < BG_POSITION_THRESHOLD;
      var nearTop    = Math.abs(top)    < BG_POSITION_THRESHOLD;
      var nearWidth  = Math.abs(width  - BG_WIDTH)  < BG_SIZE_THRESHOLD;
      var nearHeight = Math.abs(height - BG_HEIGHT) < BG_SIZE_THRESHOLD;
      
      return (nearLeft && nearTop && nearWidth && nearHeight);
    }
    
    // Process the slides in the specified range
    for (var i = firstSlide - 1; i < lastSlide; i++) {
      var slide = slides[i];
      var slideData = {
        slideNumber: i + 1,
        notes: "",
        elements: {
          TEXT: [],
          IMAGE: []
        }
      };
      
      // Extract speaker notes
      var notesPage = slide.getNotesPage();
      var speakerNotesShape = notesPage.getSpeakerNotesShape();
      if (speakerNotesShape) {
        slideData.notes = speakerNotesShape.getText().asString().trim();
      }
      
      var pageElements = slide.getPageElements();
      var tempImages = [];
      var tempText   = [];
      
      // Gather elements
      for (var j = 0; j < pageElements.length; j++) {
        var element = pageElements[j];
        var type = element.getPageElementType();
        
        // Skip group elements
        if (type == SlidesApp.PageElementType.GROUP) {
          continue;
        }
        
        // ----- SHAPE => TEXT -----
        if (type == SlidesApp.PageElementType.SHAPE) {
          var shape = element.asShape();
          var textContent = shape.getText().asString().trim();
          
          if (textContent) {
            tempText.push({
              objectId: element.getObjectId(),
              text: textContent,
              _originalIndex: j
            });
          }
        }
        
        // ----- IMAGE -----
        else if (type == SlidesApp.PageElementType.IMAGE) {
          // Always read position & size so we can do background detection
          var left   = element.getLeft();
          var top    = element.getTop();
          var width  = element.getWidth();
          var height = element.getHeight();
          
          // Determine if it's a background
          var backgroundFlag = isBackgroundImage(left, top, width, height);
          
          // Build the image object (without "type")
          var imgData = {
            objectId: element.getObjectId(),
            image_description: "",
            isBackground: backgroundFlag,
            _originalIndex: j
          };
          
          // Conditionally show position/size
          if (INCLUDE_IMAGE_POSITION) {
            imgData.position = { left: left, top: top };
          }
          if (INCLUDE_IMAGE_SIZE) {
            imgData.size = { width: width, height: height };
          }
          
          tempImages.push(imgData);
        }
      }
      
      // Sort images among themselves by approximate Y, then X
      tempImages.sort(function(a, b) {
        // We'll rely on the presence (or absence) of .position for sorting
        // If we haven't included .position in the final JSON, we can store them internally for sorting:
        // but for simplicity, let's just store them in the object anyway, not for output, just for sorting.
        // In the code above, we do have the actual 'left' & 'top'. We'll store them as hidden props:
        
        // If position isn't included for output, the .position might be undefined.
        // But we know the numeric values from the loop, so let's add them as hidden fields for sorting only:
        if (!a._pos) {
          a._pos = { 
            top:   (a.position ? a.position.top : 0), 
            left:  (a.position ? a.position.left : 0) 
          };
        }
        if (!b._pos) {
          b._pos = { 
            top:   (b.position ? b.position.top : 0), 
            left:  (b.position ? b.position.left : 0) 
          };
        }
        
        var diffY = a._pos.top - b._pos.top;
        if (Math.abs(diffY) <= Y_POSITION_THRESHOLD) {
          diffY = 0;
        }
        if (diffY !== 0) {
          return diffY;
        }
        return a._pos.left - b._pos.left;
      });
      
      // Remove temporary properties before final output
      tempText.forEach(function(item) {
        delete item._originalIndex;
      });
      tempImages.forEach(function(item) {
        delete item._originalIndex;
        delete item._pos;
      });
      
      // Assign arrays to slideData
      slideData.elements.TEXT  = tempText;
      slideData.elements.IMAGE = tempImages;
      
      data.slides.push(slideData);
    }
    
    // Convert to JSON
    var jsonString = JSON.stringify(data, null, 2);
    
    // Save in folder "slides-json-exports"
    var folderName = "slides-json-exports";
    var folderIter = DriveApp.getFoldersByName(folderName);
    var targetFolder;
    if (folderIter.hasNext()) {
      targetFolder = folderIter.next();
    } else {
      targetFolder = DriveApp.createFolder(folderName);
    }
    
    var fileName = "presentation_mapping.json";
    var file = targetFolder.createFile(fileName, jsonString, MimeType.PLAIN_TEXT);
    Logger.log("JSON file created: " + file.getUrl());
    
    return jsonString;
  }