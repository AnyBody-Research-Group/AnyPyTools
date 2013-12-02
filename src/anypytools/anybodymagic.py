"""Magic functions for running cells in various scripts."""
#-----------------------------------------------------------------------------
#  Copyright (c) 2012 The IPython Development Team.
#
#  Distributed under the terms of the Modified BSD License.
#
#  The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

# Stdlib
import errno
import os
import sys
import signal
import time
from subprocess import Popen, PIPE
import atexit
from tempfile import NamedTemporaryFile
import numpy as np
import re


# Our own packages
from IPython.core import magic_arguments
from IPython.core.magic import  (
    Magics, magics_class, line_magic, cell_magic
)
from IPython.lib.backgroundjobs import BackgroundJobManager
from IPython.utils import py3compat
from IPython.utils.process import arg_split

#-----------------------------------------------------------------------------
# Magic implementation classes
#-----------------------------------------------------------------------------

def script_args(f):
    """single decorator for adding script args"""
    args = [
        magic_arguments.argument(
            '--out', type=str,
            help="""The variable in which to store stdout from the script.
            If the script is backgrounded, this will be the stdout *pipe*,
            instead of the stderr text itself.
            """
        ),
        magic_arguments.argument(
            '--dir', type=str,
            help="""The directory to run the macro commands.
            """
        ),
        magic_arguments.argument(
            '--bg', action="store_true",
            help="""Whether to run the script in the background.
            If given, the only way to see the output of the command is
            with --out/err.
            """
        ),
        magic_arguments.argument(
            '--proc', type=str,
            help="""The variable in which to store Popen instance.
            This is used only when --bg option is given.
            """
        ),
        magic_arguments.argument(
            '--dump', action="store_true",
            help="""This will move all 'dump'ed varialbes to the ipython name
            space.
            """
        ),
    ]
    for arg in args:
        f = arg(f)
    return f

@magics_class
class AnyBodyMagics(Magics):
    """Magics for talking to scripts
    
    This defines a base `%%script` cell magic for running a cell
    with a program in a subprocess, and registers a few top-level
    magics that call %%script with common interpreters.
    """

    
    def __init__(self, shell):
        super(AnyBodyMagics,self).__init__(shell)
        self.job_manager = BackgroundJobManager()
        self.bg_processes = []
        atexit.register(self.kill_bg_processes)

    def __del__(self):
        self.kill_bg_processes()
    
    @magic_arguments.magic_arguments()
    @script_args
    @cell_magic("anybody")
    def shebang(self, line, cell):
        """Run a cell via a shell command
        
        The `%%anybody` invokes the anybody console application on the rest of
        the cell.        
        
        Parameters
        ----------
        --dir <Path>
        --out <output var>        
        --bg <>
        --proc <baground process variable >
        
        Examples
        --------
        ::
            In [1]: %%anybody
               ...: load "mymodel.any"
               ...: operation Main.MyStudy.Kinematics
               ...: run
        """
        argv = arg_split(line, posix = not sys.platform.startswith('win'))
        args, dummy = self.shebang.parser.parse_known_args(argv)
        
        
        if sys.platform != 'win32':
            raise Exception('Only works on windows')
        import _winreg
        try:        
            abpath = _winreg.QueryValue(_winreg.HKEY_CLASSES_ROOT,
                        'AnyBody.AnyScript\shell\open\command').rsplit(' ',1)[0]
            abcpath  = os.path.join(os.path.dirname(abpath),'AnyBodyCon.exe')
        except:
            raise Exception('Could not find AnyBody Modeling System installed')

        if args.dir and os.path.isdir(args.dir):
            folder = args.dir
        else:
            folder = os.getcwd()
        
        cell = cell.encode('utf8', 'replace')
        macro = cell if cell.endswith('\n') else cell+'\n'
        macrofile = NamedTemporaryFile(mode='w+b',
                                         prefix ='macro_',
                                         suffix='.anymcr',
                                         dir = folder,
                                         delete = False)
        
        macrofile.write(macro)
        macrofile.flush()

        
        
        
        cmd = [abcpath ,'--macro=', macrofile.name,'/ni', "1>&2"]        
        
        try:
            p = Popen(cmd, stdout=PIPE, stderr=PIPE, stdin=PIPE,shell= True)
        except OSError as e:
            if e.errno == errno.ENOENT:
                print "Couldn't find program: %r" % cmd[0]
                return
            else:
                raise
        
        if args.bg:
            self.bg_processes.append(p)
            self._gc_bg_processes()
            if args.out:
                self.shell.user_ns[args.out] = p.stderr
            self.job_manager.new(p.wait, daemon=True)
            if args.proc:
                self.shell.user_ns[args.proc] = p
            return
        
        try:
            #p.stdin.write(cell)
            raw_out = []
            for line in iter(p.stderr.readline, b''):
                #publish_display_data('test',{'text/plain':line.rstrip()})
                line = py3compat.bytes_to_str(line)
                print(line.rstrip())
                raw_out.append(line)
            p.communicate();
                
        except KeyboardInterrupt:
            try:
                p.send_signal(signal.SIGINT)
                time.sleep(0.1)
                if p.poll() is not None:
                    print "Process is interrupted."
                    return
                p.terminate()
                time.sleep(0.1)
                if p.poll() is not None:
                    print "Process is terminated."
                    return
                p.kill()
                print "Process is killed."
            except OSError:
                pass
            except Exception as e:
                print "Error while terminating subprocess (pid=%i): %s" \
                    % (p.pid, e)
            return
        raw_out = "\n".join(raw_out)
        if args.out:
            self.shell.user_ns[args.out] = raw_out
        
        if args.dump:
            output =  _parse_anybodycon_output(raw_out)
            for k,v in output.iteritems():
                self.shell.user_ns[k.replace('.','_')] = v
        try:
            macrofile.close()            
            os.remove(macrofile.name) 
        except:
            print 'Error removing macro file'    
    

    @line_magic("killbganybodycon")
    def killbgscripts(self, _nouse_=''):
        """Kill all BG processes started by %%anybody and its family."""
        self.kill_bg_processes()
        print "All background processes were killed."

    def kill_bg_processes(self):
        """Kill all BG processes which are still running."""
        for p in self.bg_processes:
            if p.poll() is None:
                try:
                    p.send_signal(signal.SIGINT)
                except:
                    pass
        time.sleep(0.1)
        for p in self.bg_processes:
            if p.poll() is None:
                try:
                    p.terminate()
                except:
                    pass
        time.sleep(0.1)
        for p in self.bg_processes:
            if p.poll() is None:
                try:
                    p.kill()
                except:
                    pass
        self._gc_bg_processes()

    def _gc_bg_processes(self):
        self.bg_processes = [p for p in self.bg_processes if p.poll() is None]


def _parse_anybodycon_output(strvar):
    out = {};
    dump_path = None
    for line in strvar.splitlines():
        if line.count('#### Macro command') and line.count('"Dump"'):
            me = re.search('Main[^ \"]*', line)
            if me is not None :
                dump_path = me.group(0)
        if line.endswith(';'):
            (first, last) = line.split('=')
            first = first.strip()
            last = last.strip(' ;').replace('{','[').replace('}',']')
            if dump_path is not None:
                first = dump_path
                dump_path = None
            out[first.strip()] = np.array(eval(last))
        if line.startswith('ERROR') or line.startswith('Error'): 
            if line.endswith('Path does not exist.'):
                continue # hack to avoid detecting #path error this error which is always present
            if not out.has_key('ERROR'): out['ERROR'] = []
            out['ERROR'].append(line)
    return out


_loaded = False

def load_ipython_extension(ip):
    """Load the extension in IPython."""
    global _loaded
    if not _loaded:
        ip.register_magics(AnyBodyMagics)
        _loaded = True