// -*- mode: js; js-indent-level: 2; -*-
require.undef('canvas_widget');

define('canvas_widget', ["@jupyter-widgets/base"], function(widgets) {
  var CanvasView = widgets.DOMWidgetView.extend({
  
    // Render the view.
    render: function() {
      this.canvas = document.createElement("canvas");
      this._ctx = this.canvas.getContext('2d');
      this.el.appendChild(this.canvas);
	  
	  //adds listener which triggers on click, issue with communication, this.model.get and
	  //this.model.set not working
	  this.canvas.addEventListener("mousedown", function(){
		  this.handle_mouse_event();
		  alert(click_number);
	  });
	  
      // Background for rendering on Safari etc.
      this._bg_canvas = document.createElement("canvas");
      this._bg_ctx = this._bg_canvas.getContext('2d');

      this.update()
      
      // Python -> JavaScript update
      //this.model.on('change:width', this.update, this);
      //this.model.on('change:height', this.update, this);
      //this.model.on('change:_rgba', this.update, this);
      
      // JavaScript -> Python update
      //this.value.onchange = this.value_changed.bind(this);
    },
    
    update: function() {
      var _data = this.model.get('_rgba');
      if (_data && _data.byteLength) {
        var _raw_data = new Uint8ClampedArray(_data.buffer);
        var _width = this.model.get('_image_width');
        this._image_data = new ImageData(_raw_data, _width);
        //requestAnimationFrame(this.draw_image.bind(this));
        this.draw_image();
      }
    },

    draw_image: function() {
      // Draws the image data on the canvas, scaling up if the size
      // does not match.
      var image_data = this._image_data;
      var width = this.model.get('width');
      var height = this.model.get('height');
      var im_width = image_data.width;
      var im_height = image_data.height;
	  
      debugger;
      if (0 == width && 0 == height) {
        width = im_width;
        height = im_height;
      } else if (0 == height) {
        // Preserve aspect ratio
        height = im_height * width / im_width;
      } else if (0 == width) {
        // Preserve aspect ratio
        width = im_width * height / im_height;
      }
      
      if (width == im_width && height == im_height) {
        // Simply draw.
        this.canvas.width = width;
        this.canvas.height = height;                 
        this._ctx.putImageData(image_data, 0, 0);
      } else {
        // Pre-render on background canvas, then scale
        this._bg_canvas.width = im_width;
        this._bg_canvas.height = im_height;
        this._bg_ctx.putImageData(image_data, 0, 0);

        this.canvas.width = width;
        this.canvas.height = height;                 
        this._ctx.drawImage(this._bg_canvas,
                            0, 0, im_width, im_height,
                            0, 0, width, height);
      }
    },
	
	
	// handles events using the mouse
	handle_mouse_event: function () {
		var click_number = this.model.get('clicks');
		click_number += 1;
		this.model.set('clicks', click_number);
        this.model.save_changes();
	},
	
  });
  
  
  
  return {
    CanvasView: CanvasView
  };
});
