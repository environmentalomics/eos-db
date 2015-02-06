import subprocess
import threading

class PServeThread(threading.Thread):
    """ """
    
    def __init__(self):
        self.stdout = None
        self.stderr = None
        threading.Thread.__init__(self)

    def run(self):
        """ Open pserve as a subprocess with a database server override. """
        self.p = subprocess.Popen('pserve ../../development.ini'.split(),
                             shell=False,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        self.stdout, self.stderr = self.p.communicate()

    def destroy(self):
        self.p.kill()
