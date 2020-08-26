from Client import TFTPWriteClient

if __name__ == "__main__":
    #local_filename = ".\\TestInputs\\EmptyFile.txt"
    local_filename = ".\\TestInputs\\Regular.txt"
    #local_filename = ".\\TestInputs\\SingleBlockInput.txt"
    #local_filename = ".\\TestInputs\\TwoBlockInput.txt"
    client = TFTPWriteClient(local_filename=local_filename, remote_filename=TFTPWriteClient.REMOTE_FILENAME)
    client.write()
