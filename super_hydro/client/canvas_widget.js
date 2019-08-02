// -*- mode: js; js-indent-level: 2; -*-
require.undef('canvas_widget');

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}



define('canvas_widget', ["@jupyter-widgets/base"], function(widgets) {
  var CanvasView = widgets.DOMWidgetView.extend({
    
    // Render the view.
    render: function() {
      this.canvas = document.createElement("canvas");
      this._ctx = this.canvas.getContext('2d');
      this.el.appendChild(this.canvas);

	    // adds listener which triggers on mouse events
      var events = ["mousedown", "mouseup", "mouseleave",
                    "mouseenter", "mousemove"];
      for (event of events) {
	      this.canvas.addEventListener(event, this.handle_mouse_event.bind(this));
      }
	   
	    // adds listener whih triggers on key events
      this.canvas.tabIndex = 1;
	    var key_events = ["keydown", "keyup"];
	    for (event of key_events) {
	      this.canvas.addEventListener(event, this.handle_key_event.bind(this));
      }
	  
      // Background for rendering on Safari etc.
      this._bg_canvas = document.createElement("canvas");
      this._bg_ctx = this._bg_canvas.getContext('2d');
      
      // Timing control
      this._tic = Date.now();
      this._update_requests = [];
      
      // Start the event loop.
      this.start()
      
      // Python -> JavaScript update
      //this.model.on('change:width', this.update, this);
      //this.model.on('change:height', this.update, this);
      this.model.on('change:_rgba', this.update_rgba, this);
      
      // JavaScript -> Python update
      //this.value.onchange = this.value_changed.bind(this);
    },

    /**
     * Start the event loop.  This sends a message to the server to update.
     */
    start: function() {
      requestAnimationFrame(this.send_update_request.bind(this));
    },

    /**
     * Send an update request message to the python side.
     */
    send_update_request: function() {
      this.send({'request': 'update'});
    },
    
    /**
     * This function is called whenever the model changes and does not
     * need to be registered. This behaviour is defined in
     * packages/base/src/widget.ts
     */
    update: function() {
    },

    /**
     * This function is called whenever the model changes and does not
     * need to be registered. This behaviour is defined in
     * packages/base/src/widget.ts
     */
    update_rgba: function() {
      // Remove all old requests
      while (this._update_requests.length) {
        clearTimeout(this._update_requests.pop());
      }
      
      this.do_update();
      var fps = this.model.get('fps');
      var toc = Date.now();
      var elapsed_time = toc - this._tic;
      this._tic = toc;
      var wait = 1000/fps - elapsed_time;
      wait = Math.max(0, wait);
      console.log(wait);
      this._update_requests.push(setTimeout(this.start.bind(this), wait));
    },

    do_update: function() {
      var _data = this.model.get('_rgba');
      if (_data && _data.byteLength) {
        var _raw_data = new Uint8ClampedArray(_data.buffer);
        var _width = this.model.get('_image_width');
        this._image_data = new ImageData(_raw_data, _width);
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
	  handle_mouse_event: function (event) {
	    
		  var ev = {};
		  
		  ev.type = event.type;
		  
		  //distinguish left and right click
		  if (ev.type == "mousedown" || ev.type == "mouseup"){
			  switch (event.button){
				  case 0:
					ev.type = '' + ev.type + '_left'
				  break;
				  
				  case 1:
					ev.type = '' + ev.type + '_middle'
				  break;
				  
				  case 2:
					ev.type = '' + ev.type + '_right'
				  break;
				  
				  default:
					ev.type = 'unexpected'
			  }
		  }
		  
		  // handles coordinates of mouse
		  ev.coor_X = event.offsetX;
		  ev.coor_Y = event.offsetY;
		  
		  //sends ev back to python as dictionary
		  this.model.set('mouse_event_data', ev);
		  
      this.model.save_changes();
      //console.log(event.type);
	  },
	  
	  // handle key presses
	  handle_key_event: function (event) {
		  var kev = {};
		  kev.keyCode = event.keyCode;
		  kev.type = event.type;
		  
		  this.model.set('key_event_data', kev);
		  
	  this.model.save_changes();
	  },
	  
	  
  });
  
  
  return {
    CanvasView: CanvasView
  };
});