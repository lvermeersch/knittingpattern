"""In this module you can find the parsing of knitting pattern structures."""
# attributes

ID = "id"  #: the id of a row, an instruction or a pattern
NAME = "name"  #: the name of a row
TYPE = "type"  #: the type of an instruction or the knitting pattern set
VERSION = "version"  #: the version of a knitting pattern set
INSTRUCTIONS = "instructions"  #: the instructions in a row
SAME_AS = "same as"  #: pointer to a inherit from
PATTERNS = "patterns"  #: the patterns in the knitting pattern set
ROWS = "rows"  #: the rows inside a pattern
CONNECTIONS = "connections"  #: the connections in a pattern
FROM = "from"  #: the position and row a connection comes from
TO = "to"  #: the position and row a connection goes to
START = "start"  #: the mesh index the connection starts at
#: the default mesh index the connection starts at if none is given
DEFAULT_START = 0
MESHES = "meshes"  #: the number of meshes of a connection
COMMENT = "comment"  #: a comment of a row, an instruction, anything

# constants

#: the default type of the knitting pattern set
KNITTING_PATTERN_TYPE = "knitting pattern"


class ParsingError(ValueError):

    """Mistake in the provided object to parse.

    This Error is raised if there is an error during the parsing for
    :class:`~knittingpattern.Parser.Parser`.
    """


class Parser(object):

    """Parses a knitting pattern set and anything in it."""

    def __init__(self, specification):
        """Create a parser with a specification.

        :param specification: the types and classes to use for the resulting
          object structure, preferably a
          :class:`knittingpattern.ParsingSpecification.ParsingSpecification`

        """
        self._spec = specification
        self._start()

    def _start(self):
        """Initialize the parsing process."""
        self._instruction_library = self._spec.new_default_instructions()
        self._as_instruction = self._instruction_library.as_instruction
        self._id_cache = {}
        self._pattern_set = None
        self._inheritance_todos = []
        self._instruction_todos = []

    @staticmethod
    def _to_id(id_):
        """Converts the argument to a object suitable as an identifier.

        :return: a hashable object
        """
        return tuple(id_) if isinstance(id_, list) else id_

    def _error(self, text):
        """Raise an error.

        :raises: a specified ParsingError
        :param str text: the text to include in the error message
        """
        raise self._spec.new_parsing_error(text)

    def knitting_pattern_set(self, values):
        """Parse a knitting pattern set.

        :param dict value: the specification of the knitting pattern set
        :rtype: knittingpattern.KnittingPatternSet.KnittingPatternSet
        :raises knittingpattern.KnittingPatternSet.ParsingError: if
          :paramref:`value` does not fulfill the :ref:`specification
          <FileFormatSpecification>`.

        """
        self._start()
        pattern_collection = self._new_pattern_collection()
        self._fill_pattern_collection(pattern_collection, values)
        self._create_pattern_set(pattern_collection, values)
        return self._pattern_set

    def _finish_inheritance(self):
        """Finish those who still need to inherit."""
        while self._inheritance_todos:
            prototype, parent_id = self._inheritance_todos.pop()
            parent = self._id_cache[parent_id]
            prototype.inherit_from(parent)

    def _delay_inheritance(self, prototype, parent_id):
        """Add a deleyed inheritance that is ti be resolved later.

        When calling :meth:`_finish_inheritance` this inheritance chain shall
        be resolved.
        """
        self._inheritance_todos.append((prototype, parent_id))

    def _finish_instructions(self):
        """Finish those who still need to inherit."""
        while self._instruction_todos:
            row = self._instruction_todos.pop()
            instructions = row.get(INSTRUCTIONS, [])
            row.instructions.extend(instructions)

    def _delay_instructions(self, row):
        """Add a deleyed inheritance that is ti be resolved later.

        When calling :meth:`_finish_instructions` this inheritance chain shall
        be resolved.
        """
        self._instruction_todos.append(row)

    def _new_pattern_collection(self):
        """Create a new pattern collection.

        :return: a new specified pattern collection for
          :meth:`knitting_pattern_set`
        """
        return self._spec.new_pattern_collection()

    def new_row_collection(self):
        """Create a new row collection.

        :return: a new specified row collection for the
          :meth:`knitting pattern <new_pattern>`
        """
        return self._spec.new_row_collection()

    def _fill_pattern_collection(self, pattern_collection, values):
        """Fill a pattern collection."""
        pattern = values.get(PATTERNS, [])
        for pattern_to_parse in pattern:
            parsed_pattern = self._pattern(pattern_to_parse)
            pattern_collection.append(parsed_pattern)

    def _row(self, values):
        """Parse a row."""
        row_id = self._to_id(values[ID])
        row = self._spec.new_row(row_id, values, self)
        if SAME_AS in values:
            self._delay_inheritance(row, self._to_id(values[SAME_AS]))
        self._delay_instructions(row)
        self._id_cache[row_id] = row
        return row

    def new_row(self, id_):
        """Create a new row with an id.

        :param id_: the id of the row
        :return: a row
        :rtype: knittingpattern.Row.Row
        """
        return self._spec.new_row(id_, {}, self)

    def instruction_in_row(self, row, specification):
        """Parse an instruction.

        :param row: the row of the instruction
        :param specification: the specification of the instruction
        :return: the instruction in the row
        """
        whole_instruction_ = self._as_instruction(specification)
        return self._spec.new_instruction_in_row(row, whole_instruction_)

    def _pattern(self, base):
        """Parse a pattern."""
        rows = self._rows(base.get(ROWS, []))
        self._finish_inheritance()
        self._finish_instructions()
        self._connect_rows(base.get(CONNECTIONS, []))
        id_ = self._to_id(base[ID])
        name = base[NAME]
        return self.new_pattern(id_, name, rows)

    def new_pattern(self, id_, name, rows=None):
        """Create a new knitting pattern.

        If rows is :obj:`None` it is replaced with the
        :meth:`new_row_collection`.
        """
        if rows is None:
            rows = self.new_row_collection()
        return self._spec.new_pattern(id_, name, rows, self)

    def _rows(self, spec):
        """Parse a collection of rows."""
        rows = self.new_row_collection()
        for row in spec:
            rows.append(self._row(row))
        return rows

    def _connect_rows(self, connections):
        """Connect the parsed rows."""
        for connection in connections:
            from_row_id = self._to_id(connection[FROM][ID])
            from_row = self._id_cache[from_row_id]
            from_row_start_index = connection[FROM].get(START, DEFAULT_START)
            from_row_number_of_possible_meshes = \
                from_row.number_of_produced_meshes - from_row_start_index
            to_row_id = self._to_id(connection[TO][ID])
            to_row = self._id_cache[to_row_id]
            to_row_start_index = connection[TO].get(START, DEFAULT_START)
            to_row_number_of_possible_meshes = \
                to_row.number_of_consumed_meshes - to_row_start_index
            meshes = min(from_row_number_of_possible_meshes,
                         to_row_number_of_possible_meshes)
            # TODO: test all kinds of connections
            number_of_meshes = connection.get(MESHES, meshes)
            from_row_stop_index = from_row_start_index + number_of_meshes
            to_row_stop_index = to_row_start_index + number_of_meshes
            assert 0 <= from_row_start_index <= from_row_stop_index
            produced_meshes = from_row.produced_meshes[
                from_row_start_index:from_row_stop_index]
            assert 0 <= to_row_start_index <= to_row_stop_index
            consumed_meshes = to_row.consumed_meshes[
                to_row_start_index:to_row_stop_index]
            assert len(produced_meshes) == len(consumed_meshes)
            mesh_pairs = zip(produced_meshes, consumed_meshes)
            for produced_mesh, consumed_mesh in mesh_pairs:
                produced_mesh.connect_to(consumed_mesh)

    def _get_type(self, values):
        """:return: the type of a knitting pattern set."""
        if TYPE not in values:
            self._error("No pattern type given but should be "
                        "\"{}\"".format(KNITTING_PATTERN_TYPE))
        type_ = values[TYPE]
        if type_ != KNITTING_PATTERN_TYPE:
            self._error("Wrong pattern type. Type is \"{}\" "
                        "but should be \"{}\""
                        "".format(type_, KNITTING_PATTERN_TYPE))
        return type_

    def _get_version(self, values):
        """:return: the version of :paramref:`values`."""
        return values[VERSION]

    def _create_pattern_set(self, pattern, values):
        """Create a new pattern set."""
        type_ = self._get_type(values)
        version = self._get_version(values)
        comment = values.get(COMMENT)
        self._pattern_set = self._spec.new_pattern_set(
            type_, version, pattern, self, comment
        )


def default_parser():
    """The parser with a default specification.

    :return: a parser using a
      :class:`knittingpattern.ParsingSpecification.DefaultSpecification`
    :rtype: knittingpattern.Parser.Parser
    """
    from .ParsingSpecification import DefaultSpecification
    specification = DefaultSpecification()
    return Parser(specification)


__all__ = ["Parser", "ID", "NAME", "TYPE", "VERSION", "INSTRUCTIONS",
           "SAME_AS", "PATTERNS", "ROWS", "CONNECTIONS", "FROM", "TO", "START",
           "DEFAULT_START", "MESHES", "COMMENT", "ParsingError",
           "default_parser"]
