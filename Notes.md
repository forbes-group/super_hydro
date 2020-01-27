# To Do

* Remove unnecessary dependences:
  * Definitely scipy (used for sinc...)
  * Possibly matplotlib.
  
Issues
------
* Default config file in server directory.
  * Load this first, then read user's file.
* Don't fail if no config file exists, make one.
* Simple strategy for locating the config file: use the `__file__`
  variable.
 
  `os.path.dirname(__file__)`

* Choose better port - with some sort of resolution if it is used.

   ```bash
   # Set the NBPORT variable for the user from /etc/nbports
   export NBPORT=$(sed -n -e "s/${USER}: //p" /etc/nbports)
   if [ -z "$NBPORT" ]; then
      # https://unix.stackexchange.com/a/132524/37813
      export NBPORT=$(python - <<-END
           import socket
           s = socket.socket()
           s.bind(("", 0))
           print(s.getsockname()[1])
           s.close()
           END
   )
      >&2 echo "Warning: ${USER} not in /etc/nbports.  Using random port ${NBPORT}"
   fi
   ```

   Put a default port (not 8888) in config file, then search forward
   incrementally until a free port is found.

MMF: Make simple logger.

* Refactor socket communication making sure that messages are properly
  sent and buffered.

Dependencies
============
* Consider two different clients - a lite client that has minimal
  imports (but requires the server to compute everything) and a more
  full-bodied client that can perform some computations such as the
  tracer particles to reduce server load.  The idea is to keep the
  lite client for mobile devices which cannot import numpy/scipy etc.
  
To Do
=====
When running the network_server from the notebook client, Quit does
not release zmq sockets, so one gets ZMQError: Address already in use
when trying to restart.
