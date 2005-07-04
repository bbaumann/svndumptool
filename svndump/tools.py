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
from optparse import OptionParser
import md5

from svndump import __version, copy_dump_file
from common import create_svn_date_str
from file import SvnDumpFile

__doc__ = """Various tools."""

#-------------------------------------------------------------------------------
# copy

def svndump_copy_cmdline( appname, args ):
    """
    Parses the commandline and executes the copy.

    Usage:

        >>> svndump_copy_cmdline( sys.argv[0], sys.argv[1:] )

    @type appname: string
    @param appname: Name of the application (used in help text).
    @type args: list( string )
    @param args: Commandline arguments.
    @rtype: integer
    @return: Return code (0 = OK).
    """

    usage = "usage: %s [options] source destination" % appname
    parser = OptionParser( usage=usage, version="%prog "+__version )
    (options, args) = parser.parse_args( args )

    if len( args ) != 2:
        print "specify exactly one source and one destination dumpfile."
        return 1

    copy_dump_file( args[0], args[1] )
    return 0


#-------------------------------------------------------------------------------
# export

class SvnDumpExport:
    """
    A class for exporting files from a svn dump files.
    """

    def __init__( self ):
        """
        Initialize.
        """

        # files to export, { rev -> { repos-path -> filename, ... }, ... }
        self.__exports = {}

    def add_export_file( self, revnr, repospath, filename ):
        """
        Add a file to export.

        @type revnr: integer
        @param revnr: Revision number.
        @type repospath: string
        @param repospath: Path of the file in the repository.
        @type filename: string
        @param filename: Name of the exported file.
        """

        if not self.__exports.has_key( revnr ):
            self.__exports[revnr] = {}
        self.__exports[revnr][repospath] = filename

    def execute( self, dumpfilename, directory ):
        """
        Executes the export.

        @type dumpfilename: string
        @param dumpfilename: Name of the svn dump file.
        @type directory: string
        @param directory: Directory to store the exported files.
        """

        dump = SvnDumpFile()
        dump.open( dumpfilename )

        while dump.read_next_rev():
            revnr = dump.get_rev_nr()
            if self.__exports.has_key( revnr ):
                for path, filename in self.__exports[revnr].iteritems():
                    print "r%-6d %s" % ( revnr, path )
                    nodes = dump.get_nodes_by_path( path, "ACR" )
                    saved = False
                    for node in nodes:
                        if node.has_text():
                            outfile = open( filename, "wb" )
                            node.write_text_to_file( outfile )
                            outfile.close()
                            saved = True
                            print "  saved as %s" % filename
                    if not saved:
                        if len(nodes) > 0:
                            print "  not found"
                        else:
                            print "  has no text"
        dump.close()
        return 0

def __svndump_export_opt_e( option, opt, value, parser, *args ):
    """
    Option parser callback for rename '-r from to'.
    """
    export = args[0]
    export.add_export_file( int( value[0] ), value[1], value[2] )

def svndump_export_cmdline( appname, args ):
    """
    Parses the commandline and executes the export.

    Usage:

        >>> svndump_export_cmdline( sys.argv[0], sys.argv[1:] )

    @type appname: string
    @param appname: Name of the application (used in help text).
    @type args: list( string )
    @param args: Commandline arguments.
    @rtype: integer
    @return: Return code (0 = OK).
    """

    usage = "usage: %s [options] dumpfile" % appname
    parser = OptionParser( usage=usage, version="%prog "+__version )
    export = SvnDumpExport()
    parser.add_option( "-e", "--export",
                       action="callback", callback=__svndump_export_opt_e,
                       callback_args=(export,),
                       dest=" rev repospath filename",
                       nargs=3, type="string",
                       help="adds a file to export." )
    parser.add_option( "-d", "--directory",
                       action="store", type="string",
                       dest="dir", default=".",
                       help="set the directory for the exported files." )
    (options, args) = parser.parse_args( args )

    return export.execute( args[0], options.dir )


#-------------------------------------------------------------------------------
# check

class SvnDumpCheck:
    """
    A class for checking svn dump files.
    """

    def __init__( self ):
        """
        Initialize.
        """

        # check actions
        self.__check_actions = False
        self.__history = {}
        # check dates
        self.__check_dates = False
        # check md5 sums
        self.__check_md5 = False

    def set_check_actions( self, docheck ):
        """
        Set the check actions flag to the given value.

        @type docheck: bool
        @param docheck: New value for the flag.
        """

        self.__check_actions = docheck

    def set_check_dates( self, docheck ):
        """
        Set the check dates flag to the given value.

        @type docheck: bool
        @param docheck: New value for the flag.
        """

        self.__check_dates = docheck

    def set_check_md5( self, docheck ):
        """
        Set the check md5 sums flag to the given value.

        @type docheck: bool
        @param docheck: New value for the flag.
        """

        self.__check_md5 = docheck

    def execute( self, dumpfilename ):
        """
        Check a dump file.

        @type dumpfilename: string
        @param dumpfilename: Name of the file to check.
        """

        print "\nChecking file " + dumpfilename
        dump = SvnDumpFile()
        dump.open( dumpfilename )
        rc = 0
        prev_date = ( 0, 0 )
        self.__history = {}

        while dump.read_next_rev():
            if dump.get_rev_nr() >= 3055:
                break
            self.__next_rev()
            if self.__check_dates:
                date = dump.get_rev_date()
                if date < prev_date:
                    rc = 1
                    self.__print_rev( dump.get_rev_nr() )
                    print "    rev date: %s  %10d.%06d" % (
                        dump.get_rev_date_str(), date[0], date[1] )
                    print "    previous: %s  %10d.%06d" % (
                        create_svn_date_str( prev_date ),
                        prev_date[0], prev_date[1] )
                prev_date = date
            for node in dump.get_nodes_iter():
                self.__next_node()
                if self.__check_md5 and node.has_text():
                    md = md5.new()
                    handle = node.text_open()
                    data = node.text_read( handle )
                    n = 0
                    while len(data) > 0:
                        n = n + len(data)
                        md.update( data )
                        data = node.text_read( handle )
                    node.text_close( handle )
                    md5sum = md.hexdigest()
                    if node.get_text_md5() != md5sum:
                        rc = 1
                        self.__print_node( dump.get_rev_nr(), node )
                        print "      md5 calc: %s" % md5sum
                        print "      md5 node: %s" % node.get_text+md5()
                if self.__check_actions:
                    msglist = self.__check_action( dump.get_rev_nr(), node )
                    if msglist != None:
                        rc = 1
                        self.__print_node( dump.get_rev_nr(), node )
                        for msg in msglist:
                            print "      " + msg

        dump.close()
        print [ "OK", "Not OK" ][ rc ]
        return rc

    def __next_rev( self ):
        """
        Clears the rev_printed flag.
        """
        self.__rev_printed = False

    def __print_rev( self, revnr ):
        """
        Prints the revision number if not already done.

        @type revnr: int
        @param revnr: Current revision number.
        """
        if not self.__rev_printed:
            self.__rev_printed = True
            print "  Revision %d" % revnr

    def __next_node( self ):
        """
        Clears the node_printed flag.
        """
        self.__node_printed = False

    def __print_node( self, revnr, node ):
        """
        Prints the revision number and node path if not already done.

        @type revnr: int
        @param revnr: Current revision number.
        @type node: SvnDumpNode
        @param node: Current node.
        """
        if not self.__node_printed:
            self.__node_printed = True
            self.__print_rev( revnr )
            print "    Node: %s" % node.get_path()

    def __check_action( self, revnr, node ):
        """
        Checks the action of a node and keeps it's history.

        @type revnr: int
        @param revnr: Current revision number.
        @type node: SvnDumpNode
        @param node: Current node.
        """
        path = node.get_path()
        action = node.get_action()
        if action == "add":
            # path must not exist
            if self.__node_kind( revnr, path ) != None:
                return [ "Node already exists." ]
            # parent must be a dir
            slash = path.rfind( "/" )
            if slash > 0:
                ppath = path[:slash]
                pkind = self.__node_kind( revnr, ppath )
                if pkind == None:
                    return [ "Parent doesn't exist." ]
                elif pkind != "D":
                    return [ "Parent is not a directory." ]
            # copy-from must exist
            if node.has_copy_from():
                if self.__node_kind( node.get_copy_from_rev(),
                                     node.get_copy_from_path() ) == None:
                    frompath = "  r%d %s" % ( node.get_copy_from_rev(),
                            node.get_copy_from_path() )
                    return [ "Copy-from path doesn't exist.", frompath ]
            self.__add_node( revnr, node )
        elif action == "delete":
            # path must exist
            if self.__node_kind( revnr, path ) == None:
                return [ "Node doesn't exist." ]
            self.__delete_node( revnr, node )
        else:
            # path must exist
            if self.__node_kind( revnr, path ) == None:
                return [ "Node doesn't exist." ]
            # replace = delete & add; changes can be ignored
            if action == "replace" and node.has_copy_from():
                self.__delete_node( revnr, node )
                self.__add_node( revnr, node )
        return None

    def __node_kind( self, revnr, path ):
        """
        Returns the kind of a node if it exists, else None.

        @type revnr: int
        @param revnr: Current revision number.
        @type node: string
        @param node: Path of a node.
        @rtype: string
        @return: "D" for dirs, "F" for files or None.
        """
        if not self.__history.has_key( path ):
            return None
        nodehist = self.__history[ path ]
        i = self.__rev_index( nodehist, revnr )
        if i == None:
            return None
        return nodehist[0][0]

    def __rev_index( self, nodehist, revnr ):
        """
        Returns the index into the node history or None.

        @type nodehist: list
        @param nodehist: History of a node.
        @type revnr: int
        @param revnr: Current revision number.
        """
        i = len(nodehist) - 1
        while i > 0 and revnr < nodehist[i][0]:
            i -= 1
        if i == 0:
            return None
        if revnr > nodehist[i][1] and nodehist[i][1] >= 0:
            return None
        return i

    def __add_node( self, revnr, node ):
        """
        Adds a node to the history, recursively if it has copy-from path/rev.

        @type revnr: int
        @param revnr: Current revision number.
        @type node: SvnDumpNode
        @param node: Node to add.
        """
        path = node.get_path()
        if not self.__history.has_key( path ):
            # create revision list for path
            kind = "D"
            if node.get_kind() == "file":
                kind = "F"
            self.__history[ path ] = [ ( kind ) ]
        # add revision range
        self.__history[ path ].append( [ revnr, -1 ] )
        kind = self.__history[ path ][0][0]
        # continue only if it's a dir with copy-from
        if kind == "F" or not node.has_copy_from():
            return
        # recursive copy
        cfpath = node.get_copy_from_path() + "/"
        cfpathlen = len(cfpath)
        cfrev = node.get_copy_from_rev()
        path += "/"
        for cfnodepath in self.__history.keys()[:]:
            if cfnodepath.startswith( cfpath ):
                cfnodehist = self.__history[cfnodepath]
                i = self.__rev_index( cfnodehist, cfrev )
                if i != None:
                    npath = path + cfnodepath[cfpathlen:]
                    # add new path
                    if not self.__history.has_key( npath ):
                        # create revision list for npath
                        kind = "D"
                        if node.get_kind() == "file":
                            kind = "F"
                        self.__history[ npath ] = [ cfnodehist[0] ]
                    # add revision range
                    self.__history[ npath ].append( [ revnr, -1 ] )


    def __delete_node( self, revnr, node ):
        """
        Deletes a node from the history, recursively if it is a directory.

        @type revnr: int
        @param revnr: Current revision number.
        @type node: SvnDumpNode
        @param node: Node to add.
        """
        # set end revision
        path = node.get_path()
        self.__history[ path ][-1][1] = revnr - 1
        kind = self.__history[ path ][0][0]
        # continue only if it's a dir
        if kind == "F":
            return
        # recursive delete
        path += "/"
        for nodepath in self.__history.keys()[:]:
            if nodepath.startswith( path ):
                nodehist = self.__history[nodepath]
                if nodehist[-1][1] == -1:
                    nodehist[-1][1] = revnr - 1

def svndump_check_cmdline( appname, args ):
    """
    Parses the commandline and executes the check.

    Usage:

        >>> svndump_check_cmdline( sys.argv[0], sys.argv[1:] )

    @type appname: string
    @param appname: Name of the application (used in help text).
    @type args: list( string )
    @param args: Commandline arguments.
    @rtype: integer
    @return: Return code (0 = OK).
    """

    usage = "usage: %s [options] dumpfiles..." % appname
    parser = OptionParser( usage=usage, version="%prog "+__version )
    check = SvnDumpCheck()
    parser.add_option( "-a", "--check-actions",
                       action="store_true", dest="check_actions", default=False,
                       help="check actions like add/change/delete" )
    parser.add_option( "-d", "--check-dates",
                       action="store_true", dest="check_dates", default=False,
                       help="check that svn:date increases" )
    parser.add_option( "-m", "--check-md5",
                       action="store_true", dest="check_md5", default=False,
                       help="check md5 sums of the files" )
    parser.add_option( "-A", "--all-checks",
                       action="store_true", dest="check_all", default=False,
                       help="do all checks" )
    (options, args) = parser.parse_args( args )

    checks = False
    if options.check_actions or options.check_all:
        check.set_check_actions( True )
        checks = True
    if options.check_dates or options.check_all:
        check.set_check_dates( True )
        checks = True
    if options.check_md5 or options.check_all:
        check.set_check_md5( True )
        checks = True

    if not checks:
        print "Please specify at least one check option."
        return 0

    rc = 0
    for filename in args:
        if check.execute( filename ) != 0:
            rc = 1
    return rc

#-------------------------------------------------------------------------------
# log

class SvnDumpLog:
    """
    A class for checking svn dump files.
    """

    def __init__( self ):
        """
        Initialize.
        """

        # verbose
        self.__verbose = False

    def set_verbose( self, verbose ):
        """
        Set the verbose flag to the given value.

        @type verbose: bool
        @param verbose: New value for the flag.
        """

        self.__verbose = verbose

    def execute( self, dumpfilename ):
        """
        Print log of a dump file.

        @type dumpfilename: string
        @param dumpfilename: Name of the file to log.
        """

        print "\n\n" + "=" * 72
        line = "-" * 72
        print "Dumpfile: " + dumpfilename
        dump = SvnDumpFile()
        dump.open( dumpfilename )
        actions = { "add":"A", "change":"M", "delete":"D", "replace":"R" }

        while dump.read_next_rev():
            revnr = dump.get_rev_nr()
            author = dump.get_rev_author()
            date = dump.get_rev_date_str()
            log = dump.get_rev_log()
            linecnt = len( log.split( "\n" ) )
            lines = "%d line" % linecnt
            if linecnt > 1:
                lines += "s"
            print line
            print "r%d | %s | %s | %s" % ( revnr, author, date, lines )
            if self.__verbose:
                print "Changed paths:"
                for node in dump.get_nodes_iter():
                    action = actions[node.get_action()]
                    path = node.get_path()
                    if path == "" or path[0] != "/":
                        path = "/" + path
                    if node.has_copy_from():
                        fpath = node.get_copy_from_path()
                        frev = node.get_copy_from_rev()
                        if fpath == "" or fpath[0] != "/":
                            fpath = "/" + fpath
                        path += " (from %s:%d)" % ( fpath, frev )
                    print "   %s %s" % ( action, path )
            print "\n" + log.rstrip() + "\n"

        print line
        dump.close()
        return 0

def svndump_log_cmdline( appname, args ):
    """
    Parses the commandline and executes the log.

    Usage:

        >>> svndump_log_cmdline( sys.argv[0], sys.argv[1:] )

    @type appname: string
    @param appname: Name of the application (used in help text).
    @type args: list( string )
    @param args: Commandline arguments.
    @rtype: integer
    @return: Return code (0 = OK).
    """

    usage = "usage: %s [options] dumpfiles..." % appname
    parser = OptionParser( usage=usage, version="%prog "+__version )
    log = SvnDumpLog()
    parser.add_option( "-v", "--verbose",
                       action="store_true", dest="verbose", default=False,
                       help="verbose output" )
    (options, args) = parser.parse_args( args )

    log.set_verbose( options.verbose )

    rc = 0
    for filename in args:
        if log.execute( filename ) != 0:
            rc = 1
    return rc
