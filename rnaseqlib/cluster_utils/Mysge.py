import os, os.path, subprocess, sys, time, getpass
from optparse import OptionParser

def waitUntilDone(jobID, sleep=1):
    """ Waits until a job ID is no longer found in the qstat output """
    while True:
        output = subprocess.Popen("qstat -j %i"%jobID, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()

        if "Following jobs do not exist:" in output[1]:
            break
        time.sleep(sleep)
        
def launchJob(cmd, scriptOptions, verbose=True, test=False, fast=True,
              queue_type="quick", scratchDir="/tmp"):
    """
    Submits a job on the cluster which will run command 'cmd', with options 'scriptOptions'

    Optionally:
    verbose: output the job script
    test: don't actually submit the job script (usually used in conjunction with verbose)
    fast: submit only to the fast nodes on coyote

    Returns a job ID if the job was submitted properly
    """

    if type(cmd) not in [type(list()), type(tuple())]:
        cmd = [cmd]

    scriptOptions.setdefault("workingdir", os.getcwd())
    scriptOptions.setdefault("nodes", "1")
    scriptOptions.setdefault("ppn", "1")
    scriptOptions.setdefault("jobname", os.path.basename(sys.argv[0]))
    scriptOptions.setdefault("scriptuser", getpass.getuser())
    scriptOptions.setdefault("queue", queue_type)
    scriptOptions.setdefault("outdir", "")

    scriptOptions["command"] = " ".join(cmd)

    if verbose:
        print "==SUBMITTING TO CLUSTER=="
        print cmd
        print scriptOptions
        
    pid = os.getpid()
    outscriptName = "%s.%i"%(scriptOptions["jobname"], pid)
    
    #scriptOptions["outf"] = os.path.abspath(os.path.join(scriptOptions["outdir"], outscriptName+".out"))
    #print "Dumping script to: %s" %(scriptOptions["outf"])

    if fast:
        assert scriptOptions["nodes"] == "1", "Can only choose specific nodes if you're not restricting jobs to the fast nodes."
        scriptOptions["nodes"] = "1:E5450"

    
    outtext = """#!/bin/bash

#$ -N %(jobname)s
#$ -S /bin/bash 
##$ -pe %(ppn)s
#$ -V 
#$ -j y
#$ -cwd
#$ -o %(outdir)s

echo $HOSTNAME
echo Working directory is %(workingdir)s
cd %(workingdir)s

echo "%(command)s"
%(command)s
echo "===== %(command)s finished =====" """ % scriptOptions

    if verbose:
        print outscriptName
        print outtext
    
    tmpScriptPath = os.path.join(scriptOptions["outdir"], "%s"%outscriptName) 
    print tmpScriptPath
    f = open(tmpScriptPath, "w")
    f.write(outtext)
    f.close()

    call = "qsub %s" % tmpScriptPath

    if not test:
        try:
            if verbose:
                print "CALL:", call

            qsub = subprocess.Popen(call, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	    print "Executing: ", scriptOptions["command"]
            output = qsub.communicate()

            if output[0].startswith("Your job "):
                jobID = int(output[0].split(" ")[2])

                if verbose:
                    print "Process launched with job ID:", jobID

                return jobID
            else:
                raise Exception("Failed to launch job '%s': %s"%(outscriptName, str(output)))
        except:
            print "failing..."
            raise
    return None

    
if __name__ == "__main__":
    usage = "%prog [options] command\n Automatically creates a job script for the command provided;"+\
        "allows running a script with input arguments, as well as specifying various cluster options"
    
    parser = OptionParser(usage=usage)

    parser.add_option("-d", "--dir", dest="workingdir", help="Working directory (default: current)")
    parser.add_option("-n", "--nodes", dest="nodes", help="Number of nodes or a comma-separated list of nodes to launch to")
    parser.add_option("-p", "--ppn", dest="ppn", help="Requested number of processors (per node) (default: 1)")
    parser.add_option("-j", "--jobname", dest="jobname", help="Job name (default: Mypbm.PID)")
    parser.add_option("-q", "--queue", dest="queue", help="Queue to submit to (default: short)")
    parser.add_option("-o", "--outdir", dest="outdir", help="Directory to save output file to (default:)")
    parser.add_option("-v", "--verbose", dest="verbose", help="Show output script on command line", action="store_true", default=False)
    parser.add_option("-t", "--test", dest="test", help="Write script file but don't run it", default=False,
                      action="store_true")
    parser.add_option("-w", "--wait", dest="wait", help="Wait until job has finished", default=False,
                      action="store_true")
    parser.add_option("-f", "--fast", dest="fast", help="Only submit jobs to the fast nodes; shouldn't be "+\
                          "specified at the same time as -n.", default=False,
                      action="store_true")
    
    (options, args) = parser.parse_args()

    if len(args) == 0:
        parser.error("Need to define command to run")
    if options.fast and options.nodes != "1":
        raise Exception("Can only specify either -n or -f.")

    
    scriptOptions = vars(options)

    # delete those options that weren't specified on the command line, as we would like to
    # define the default values for these options in the actual call to launchJob()
    for key in scriptOptions.keys():
        if scriptOptions[key] == None:
            del scriptOptions[key]
            
    jobID = launchJob(args, scriptOptions, options.verbose, options.test, fast=options.fast)

    if jobID!=None and options.wait:
        waitUntilDone(jobID)



