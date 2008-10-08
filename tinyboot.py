#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Tiny bootstrapping interpreter for the first bootstrap stage.

Implements an extremely minimal Forth-like language, used to write
tinyboot1.tbf1.

The theory is that first we 'compile' the program by reading through
it to find compile-time definitions and actions, which sets up the
initial state of memory; then we 'run' the program by directly
interpreting its text, given that initial state.

"""
import sys, cgitb
cgitb.enable(format='text')

def debug(text):
    sys.stderr.write(text + "\n")

start_address = None
memory = []                  # a list of bytes represented as integers
stack  = []
rstack = []

### Compile-time actions.
# Note that these should leave program_counter pointing after the
# last byte they consume.

program_counter = 0

def current_byte():
    return program[program_counter]

def eat_byte():
    global program_counter
    current_byte = program[program_counter]
    program_counter += 1
    return current_byte

def peek_byte():
    global program_counter
    program_counter += 1
    return program[program_counter]

def eat_comment():
    while peek_byte() != ')':

def advance_past_whitespace():
    if current_byte() not in ' \n': return
    while peek_byte() in ' \n':

def push_dataspace_label(n):
    return lambda: stack.append(n)

def dataspace_label():
    "Define a label in data space."
    advance_past_whitespace()
    name = eat_byte()
    run_time_dispatch[name] = push_dataspace_label(len(memory))

def call_function(n):
    def rv():
        global program_counter
        rstack.append(program_counter)
        program_counter = n
    return rv

def define_function():
    advance_past_whitespace()
    name = eat_byte()
    run_time_dispatch[name] = call_function(program_counter)

def read_number():
    start = program_counter
    while eat_byte() in '0123456789':
    return int(program[start:program_counter])

def literal_byte():
    advance_past_whitespace()
    memory.append(read_number())

def as_bytes(num):
    "Convert a 32-byte number into a little-endian byte sequence."
    return [num & 255, num >> 8 & 255, num >> 16 & 255, num >> 24 & 255]

def literal_word():
    "Compile a little-endian literal 32-byte number into data space."
    advance_past_whitespace()
    memory.extend(as_bytes(read_number()))

def allocate_space():
    advance_past_whitespace()
    memory.extend([0] * read_number())

def set_start_address():
    global start_address
    start_address = program_counter

def nop(): pass

# We have to find the backwards jump targets for loops while scanning
# forward.  Otherwise we’d have to find them by scanning backwards,
# and you can’t correctly skip comments that way, since comments don’t
# nest.

jump_targets = {}

def start_conditional():
    stack.append(program_counter)

def end_conditional():
    jump_targets[stack.pop()] = program_counter

start_loop = start_conditional

def end_loop():
    jump_targets[program_counter] = stack.pop()

compile_time_dispatch = {
    '(': eat_comment,
    'v': dataspace_label,
    ':': define_function,
    'b': literal_byte,
    '#': literal_word,
    '*': allocate_space,
    '^': set_start_address,
    '[': start_conditional, ']': end_conditional,
    '{': start_loop,        '}': end_loop,
    ' ': nop, '\n': nop,
}

def tbfcompile():
    while program_counter < len(program):
        byte = eat_byte()
        if byte in compile_time_dispatch:
            compile_time_dispatch[byte]()
        elif byte in run_time_dispatch:
            pass                 # ignore things from run-time for now
        else:
            excerpt_beginning = max(0, program_counter - 10)
            assert False, '%r not defined at %r' % \
                   (byte, program[excerpt_beginning:program_counter])

### Run-time actions.
# Execution should pretty much stay inside of functions, and we
# shouldn't run into any compile-time actions there, right?
# Except maybe comments.

def write_out():
    "Given an address and a count, write out some memory to stdout."
    count = stack.pop()
    address = stack.pop()
    debug('writing address %d, count %d' % (address, count))
    sys.stdout.write(''.join([chr(memory[ii])
                              for ii in range(address, address+count)]))

def quit():
    sys.exit(0)

def add():
    stack.append((stack.pop() + stack.pop()) & 0xFfffFfff)

def push_literal():
    global program_counter
    program_counter -= 1
    stack.append(read_number())

def decode(bytes):
    return bytes[0] | bytes[1] << 8 | bytes[2] << 16 | bytes[3] << 24

def fetch():
    addr = stack.pop()
    stack.append(decode(memory[addr:addr+4]))

def store():
    addr = stack.pop()
    memory[addr:addr+4] = as_bytes(stack.pop())

def store_byte():
    addr = stack.pop()
    memory[addr] = stack.pop() & 255

def bitwise_not():
    stack.append(stack.pop() ^ 0xFfffFfff)

def less_than():
    b = stack.pop()
    a = stack.pop()
    if a < b:
        stack.append(1)
    else:
        stack.append(0)

def return_from_function():
    global program_counter
    program_counter = rstack.pop()

def read_byte():
    byte = sys.stdin.read(1)
    if byte == '':
        stack.append(-1)
    else:
        stack.append(ord(byte))

def conditional():
    if stack.pop(): return
    global program_counter
    program_counter = jump_targets[program_counter]

def loop():
    if not stack.pop(): return
    global program_counter
    program_counter = jump_targets[program_counter]


run_time_dispatch = {    
    '(': eat_comment,
    'W': write_out,
    'G': read_byte,
    'Q': quit,
    '+': add,
    '~': bitwise_not,
    '<': less_than,
    '@': fetch,
    '!': store,
    # 'f': fetch_byte, not yet needed
    's': store_byte,
    ';': return_from_function,
    '[': conditional, ']': nop,
    '{': nop,         '}': loop,
    ' ': nop, '\n': nop,
}

for digit in '0123456789': run_time_dispatch[digit] = push_literal


def tbfrun():
    assert start_address is not None
    global program_counter
    program_counter = start_address
    while True:
        run_time_dispatch[eat_byte()]()

def main(infile):
    global program
    program = infile.read()
    tbfcompile()
    tbfrun()
    assert False, "tbfrun returned"

if __name__ == '__main__': main(file(sys.argv[1]))
