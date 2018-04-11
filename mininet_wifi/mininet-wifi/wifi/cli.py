import sys

from mininet.cli import CLI
from mininet_original.log import output, error

class CLI_wifi(CLI):
    "Simple command-line interface to talk to nodes."

    def __init__(self, mininet, stdin=sys.stdin, script=None):
        CLI.__init__(self, mininet, stdin=sys.stdin, script=None)

    def do_stop(self, line):
        "stop mobility for a while"
        self.mn.stop_simulation()

    def do_start(self, line):
        "pause mobility for a while"
        self.mn.start_simulation()

    def do_distance(self, line):
        "Distance between two nodes."
        args = line.split()
        if len(args) != 2:
            error('invalid number of args: distance [sta or ap] [sta or ap]\n')
        elif len(args) == 2 and args[ 0 ] == args[ 1 ]:
            error('invalid. Source and Destination are equals\n')
        else:
            self.mn.get_distance(*args)

    def do_dpctl(self, line):
        """Run dpctl (or ovs-ofctl) command on all switches.
           Usage: dpctl command [arg1] [arg2] ..."""
        args = line.split()
        if len(args) < 1:
            error('usage: dpctl command [arg1] [arg2] ...\n')
            return
        nodesL2 = self.mn.switches + self.mn.aps
        for sw in nodesL2:
            output('*** ' + sw.name + ' ' + ('-' * 72) + '\n')
            output(sw.dpctl(*args))

    prompt = 'mininet_wifi> '

    helpStr = (
        'You may also send a command to a node using:\n'
        '  <node> command {args}\n'
        'For example:\n'
        '  mininet> h1 ip addr\n'
        '\n'
        'The interpreter automatically substitutes IP addresses\n'
        'for node names when a node is the first arg, so commands\n'
        'like\n'
        '  mininet> h2 ping h3\n'
        'should work.\n'
        '\n'
        'Some character-oriented interactive commands require\n'
        'noecho:\n'
        '  mininet> noecho h2 vi foo.py\n'
        'However, starting up an xterm/gterm is generally better:\n'
        '  mininet> xterm h2\n\n'
    )
