#!/usr/bin/env python
#===============================================================================
#
# Copyright (C) 2003 Martin Furter <mf@rola.ch>
#
# This file is part of SvnDumpTool
#
# SvnDumpTool is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# SvnDumpTool is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with SvnDumpTool; see the file COPYING.  If not, write to
# the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
#
#===============================================================================

import sys

from svndump import __version
from svndump.diff import svndump_diff_cmdline
from svndump.merge import svndump_merge_cmdline
from svndump.eolfix import svndump_eol_fix_cmdline
from svndump.tools import svndump_copy_cmdline, svndump_export_cmdline, \
                          svndump_check_cmdline, svndump_log_cmdline, \
                          svndump_join_cmdline, svndump_split_cmdline

def __help( appname, args ):
    print ""
    print "svndumptool.py command [options]"
    print ""
    print "  commands:"
    print "    check        check a dumpfile"
    print "    copy         copy a dumpfile"
    print "    diff         show differences between two dump files"
    print "    eolfix       fix EOL of text files in a dump"
    print "    export       export files from a dumpfile"
    print "    join         join dumpfiles"
    print "    log          show the log of a dumpfile"
    print "    merge        merge dump files"
    print "    split        split dump files"
    print "    --version    print the version"
    print ""
    print "  use 'svndumptool.py command -h' for help about the commands."
    print ""
    return 0

def __print_version( appname, args ):
    print appname + " " + __version
    return 0

if __name__ == '__main__':
    funcs = {
        "check":    svndump_check_cmdline,
        "copy":     svndump_copy_cmdline,
        "diff":     svndump_diff_cmdline,
        "eolfix":   svndump_eol_fix_cmdline,
        "export":   svndump_export_cmdline,
        "join":     svndump_join_cmdline,
        "log":      svndump_log_cmdline,
        "merge":    svndump_merge_cmdline,
        "split":    svndump_split_cmdline
    }
    appname = sys.argv[0].replace( "\\", "/" )
    n = appname.rfind( "/" )
    if n >= 0:
        appname = appname[n+1:]
    pfx = appname[0:7]
    cmd = appname[7:-3]
    sfx = appname[-3:]
    func = __help;
    args = []
    argidx = 0
    if pfx == "svndump" and sfx == ".py" and funcs.has_key( cmd ):
        func = funcs[cmd]
        argidx = 1
    elif len( sys.argv ) > 1:
        cmd = sys.argv[1]
        if funcs.has_key( cmd ):
            func = funcs[cmd]
            appname += " " + cmd
        elif cmd == "--version":
            func = __print_version
        argidx = 2
    if argidx < len( sys.argv ):
        args = sys.argv[argidx:]
    sys.exit( func( appname, args ) )

