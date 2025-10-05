LANGUAGE_SAMPLES = {'arduino': 'void setup() {\n  Serial.begin(9600);\n}\n\nvoid loop() {\n}\n',
 'c': '#include <stdio.h>\nint main(void) {\n    return 0;\n}\n',
 'chatito': '%[intent]\n    - hello\n',
 'clojure': '(ns greeter)\n\n(defn greet [name]\n  (str "Hello " name))\n',
 'commonlisp': '(defun greet (name)\n  (format nil "Hello ~a" name))\n',
 'cpp': '#include <iostream>\n'
        'int main() {\n'
        '    std::cout << "Hello" << std::endl;\n'
        '    return 0;\n'
        '}\n',
 'csharp': 'public interface IGreeter\n{\n    string Greet(string name);\n}\n',
 'd': 'import std.stdio;\nvoid main() {\n    writeln("Hello");\n}\n',
 'dart': "class Person {\n  String greet(String name) => 'Hello $name';\n}\n",
 'elisp': '(defun greeter (name)\n  (format "Hello %s" name))\n',
 'elixir': 'defmodule Greeter do\n  def greet(name) do\n    "Hello #{name}"\n  end\nend\n',
 'elm': 'module Main exposing (Person, greet)\n'
        '\n'
        'type alias Person =\n'
        '    { name : String }\n'
        '\n'
        '\n'
        'greet : Person -> String\n'
        'greet person =\n'
        '    "Hello " ++ person.name\n',
 'gleam': 'import gleam/string\n'
          '\n'
          'pub fn greet(name: String) -> String {\n'
          '  string.concat(["Hello ", name])\n'
          '}\n',
 'go': 'package main\n'
       '\n'
       'type Greeter struct{}\n'
       '\n'
       'func (g Greeter) Greet(name string) string {\n'
       '    return "Hello " + name\n'
       '}\n',
 'hcl': 'resource "aws_vpc" "main" {\n  cidr_block = "10.0.0.0/16"\n}\n',
 'java': 'public class Greeting {\n'
         '    public String greet(String name) {\n'
         '        return "Hello " + name;\n'
         '    }\n'
         '}\n',
 'javascript': 'export class Person {\n  greet(name) {\n    return `Hello ${name}`;\n  }\n}\n',
 'kotlin': 'class Greeting {\n    fun greet(name: String): String = "Hello $name"\n}\n',
 'lua': 'local function greet(name)\n  return "Hello " .. name\nend\n\nreturn { greet = greet }\n',
 'matlab': 'function greeting = Person(name)\n  greeting = ["Hello " name];\nend\n',
 'ocaml': 'module Greeter = struct\n  let greet name = "Hello " ^ name\nend\n',
 'ocaml_interface': 'module Greeter : sig\n  val greet : string -> string\nend\n',
 'php': '<?php\nfunction greet($name) {\n    return "Hello $name";\n}\n',
 'pony': 'actor Greeter\n  be greet(name: String) =>\n    None\n',
 'properties': 'database.url=jdbc://example\n',
 'python': 'class Person:\n'
           '    def __init__(self, name: str) -> None:\n'
           '        self.name = name\n'
           '\n'
           '    def greet(self) -> str:\n'
           '        return f"Hello {self.name}"\n',
 'r': 'calculate <- function(x) {\n  x + 1\n}\n',
 'racket': '#lang racket\n\n(define (greet name)\n  (string-append "Hello " name))\n',
 'ruby': 'class Greeter\n  def greet(name)\n    "Hello #{name}"\n  end\nend\n',
 'rust': 'pub struct Person;\n'
         '\n'
         'impl Person {\n'
         '    pub fn greet(name: &str) -> String {\n'
         '        format!("Hello {}", name)\n'
         '    }\n'
         '}\n',
 'scala': 'object Greeter {\n  def greet(name: String): String = s"Hello $name"\n}\n',
 'solidity': '// SPDX-License-Identifier: MIT\n'
             'pragma solidity ^0.8.0;\n'
             '\n'
             'contract SimpleStorage {\n'
             '    uint256 public storedData;\n'
             '}\n',
 'swift': 'struct Greeter {\n'
          '    func greet(name: String) -> String {\n'
          '        "Hello \\(name)"\n'
          '    }\n'
          '}\n',
 'tsx': "import React from 'react';\n"
        '\n'
        'export interface UserProps {\n'
        '  name: string;\n'
        '}\n'
        '\n'
        'export const UserCard: React.FC<UserProps> = ({ name }) => (\n'
        '  <div>{name}</div>\n'
        ');\n',
 'typescript': 'export function greet(name: string): string {\n  return `Hello ${name}`;\n}\n',
 'udev': 'SUBSYSTEM=="usb", ACTION=="add", RUN+="/usr/bin/USB_DRIVER"\n'}
