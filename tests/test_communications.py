from argparse import Namespace
import multiprocessing
# import os.path
# import sys

import numpy as np

import pytest

from super_hydro import communication


shape = (100, 200, 300)
np.random.seed(1)
A_int = np.arange(10, dtype=int)
A_complex = np.random.random(shape) + 1j*np.random.random(shape)


def run_server(host='localhost', port=12654):
    opts = Namespace(host=host, port=port)
    server = communication.Server(opts=opts)

    # Receive a simple request.
    while server.recv() != b"Start":
        server.respond(b"No! I have not started.")
    server.respond(b"Started")
        
    while True:
        request = server.recv()
        if request == b"Get List":
            server.send([1, 2, 4])
        elif request == b"Get Int Array":
            server.send_array(A_int)
        elif request == b"Get Complex Array":
            server.send_array(A_complex)

        elif request == b"Send List":
            assert server.get(response=b"Oh boy, a list!") == [1, 2, 4]
        elif request == b"Send Int Array":
            A = server.get_array(response=b"Oh boy, an int array!")
            assert A.dtype == np.int
            assert np.allclose(A, A_int)
        elif request == b"Send Complex Array":
            A = server.get_array(response=b"Oh boy, a complex array!")
            assert A.dtype == np.complex
            assert np.allclose(A, A_complex)
        elif request == b"Quit":
            server.respond(b"Quitting")
            break
        else:
            server.respond(b"I don't know how to " + request)


def run_client(host='localhost', port=12654):
    opts = Namespace(host=host, port=port)
    client = communication.Client(opts=opts)

    response = client.request(b"Quit")
    assert response == b"No! I have not started."
    
    response = client.request(b"Start")
    assert response == b"Started"

    response = client.request(b"Quitt")
    assert response == b"I don't know how to Quitt"

    li = client.get(b"Get List")
    assert li == [1, 2, 4]

    A = client.get_array(b"Get Int Array")
    assert A.dtype == np.int
    assert np.allclose(A, A_int)

    A = client.get_array(b"Get Complex Array")
    assert A.dtype == np.complex
    assert np.allclose(A, A_complex)

    response = client.send(b"Send List", [1, 2, 4])
    assert response == b"Oh boy, a list!"

    response = client.send_array(b"Send Int Array", A_int)
    assert response == b"Oh boy, an int array!"

    response = client.send_array(b"Send Complex Array", A_complex)
    assert response == b"Oh boy, a complex array!"
        
    response = client.request(b"Quit")
    assert response == b"Quitting"


@pytest.mark.skip("Known communication failure.")
def test_client_server():
    server_thread = multiprocessing.Process(target=run_server)
    server_thread.start()
    run_client()
    server_thread.join()
