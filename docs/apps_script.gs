function extractPresentationDataAsJson(startSlide, endSlide) {
  // ---- CONFIGURATION OPTIONS ----
  var INCLUDE_IMAGE_POSITION = false;
  var INCLUDE_IMAGE_SIZE     = false;
  var INCLUDE_LAYOUT         = true;
  
  // Add minimum image size threshold
  var MIN_IMAGE_SIZE = 25;  // minimum pixels for both width and height
  
  // Add supported aspect ratios and their decimal values
  var SUPPORTED_RATIOS = {
      "1:1": { ratio: 1.0, tolerance: 0.1 },
      "3:4": { ratio: 0.75, tolerance: 0.1 },
      "4:3": { ratio: 1.33333, tolerance: 0.1 },
      "9:16": { ratio: 0.5625, tolerance: 0.1 },
      "16:9": { ratio: 1.77778, tolerance: 0.1 }
  };
  
  // If two images' Y positions differ by <= this threshold, treat them as on the same "row"
  var Y_POSITION_THRESHOLD = 10;
  
  // Background image detection thresholds
  var BG_POSITION_THRESHOLD = 15;  // px away from (0,0)
  var BG_SIZE_THRESHOLD     = 50;  // px difference from 720x405
  var BG_WIDTH  = 720;            // typical background width
  var BG_HEIGHT = 405;            // typical background height

  // Layout mapping for standard layouts
  var LAYOUT_MAPPING = {
      BLANK: 'BLANK',
      CAPTION_ONLY: 'CAPTION_ONLY',
      TITLE: 'TITLE',
      TITLE_AND_BODY: 'TITLE_AND_BODY',
      TITLE_AND_TWO_COLUMNS: 'TITLE_AND_TWO_COLUMNS',
      TITLE_ONLY: 'TITLE_ONLY',
      ONE_COLUMN_TEXT: 'ONE_COLUMN_TEXT',
      MAIN_POINT: 'MAIN_POINT',
      SECTION_HEADER: 'SECTION_HEADER'
  };


  function determineAspectRatio(width, height) {
      if (!width || !height) return "1:1"; // Default if dimensions are invalid
      
      var imageRatio = width / height;
      var closestRatio = "1:1";  // Default
      var smallestDiff = Infinity;
      
      Logger.log("Calculating aspect ratio for dimensions: " + width + "x" + height + 
                " (ratio: " + imageRatio.toFixed(4) + ")");
      
      for (var ratio in SUPPORTED_RATIOS) {
          var targetRatio = SUPPORTED_RATIOS[ratio].ratio;
          var tolerance = SUPPORTED_RATIOS[ratio].tolerance;
          var diff = Math.abs(imageRatio - targetRatio);
          
          Logger.log("  Comparing to " + ratio + " (diff: " + diff.toFixed(4) + ")");
          
          // If within tolerance and closer than previous best match
          if (diff < tolerance && diff < smallestDiff) {
              smallestDiff = diff;
              closestRatio = ratio;
              Logger.log("    New best match found: " + ratio);
          }
      }
      
      return closestRatio;
  }
  
  // Add function to check if image meets minimum size requirements
  function meetsMinimumSize(width, height) {
      return width >= MIN_IMAGE_SIZE && height >= MIN_IMAGE_SIZE;
  }
  
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

  /**
   * Attempt to identify the slide's layout
   * Returns undefined for custom layouts
   */
  function identifySlideLayout(slide) {
      try {
          var layout = slide.getLayout();
          // Convert layout to string and clean up
          var layoutName = layout.toString().replace('Layout.', '').trim();
          
          // Check if it's a standard layout
          if (LAYOUT_MAPPING[layoutName]) {
              return LAYOUT_MAPPING[layoutName];
          }
          
          // If we don't recognize the layout, return undefined
          // This will omit the layout field from the JSON for custom layouts
          return undefined;
          
      } catch (e) {
          Logger.log('Could not determine layout for slide: ' + e.toString());
          return undefined;
      }
  }
  
  // Process the slides in the specified range
  for (var i = firstSlide - 1; i < lastSlide; i++) {
    var slide = slides[i];
    var slideData = {
      slideNumber: i + 1,
      exists: true,
      notes: "",
      elements: {
          TEXT: [],
          IMAGE: []
      }
    };
    
    // Add layout if available and enabled
    if (INCLUDE_LAYOUT) {
        var layout = identifySlideLayout(slide);
        if (layout) {
            slideData.layout = layout;
        }
    }
    
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
          var left   = element.getLeft();
          var top    = element.getTop();
          var width  = element.getWidth();
          var height = element.getHeight();
          
          // Only add image if it meets minimum size requirements
          if (meetsMinimumSize(width, height)) {
              // Determine if it's a background
              var backgroundFlag = isBackgroundImage(left, top, width, height);
              
              // Build the image object
              var imgData = {
                  objectId: element.getObjectId(),
                  image_prompt: "",
                  isBackground: backgroundFlag,
                  aspect_ratio: determineAspectRatio(width, height),  // Add aspect ratio
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
          } else {
              Logger.log("Skipping image due to size: " + width + "x" + height);
          }
      }
    }
    
    // Sort images among themselves by approximate Y, then X
    tempImages.sort(function(a, b) {
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