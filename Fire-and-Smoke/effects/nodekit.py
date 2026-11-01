# SPDX-License-Identifier: GPL-3.0-or-later
"""Small helpers for building node trees in code, shared by geometry and shader trees."""

import bpy


class Kit:
    def __init__(self, tree):
        self.tree = tree

    def node(self, idname, **props):
        node = self.tree.nodes.new(idname)
        for key, value in props.items():
            setattr(node, key, value)
        return node

    def plug(self, socket, value):
        """Link a socket, or set a plain value as the socket's default."""
        if isinstance(value, bpy.types.NodeSocket):
            self.tree.links.new(value, socket)
        elif value is not None:
            socket.default_value = value

    def math(self, operation, a, b=None, c=None, clamp=False):
        node = self.node("ShaderNodeMath", operation=operation, use_clamp=clamp)
        for index, value in enumerate((a, b, c)):
            self.plug(node.inputs[index], value)
        return node.outputs[0]

    def add(self, a, b):
        return self.math("ADD", a, b)

    def sub(self, a, b):
        return self.math("SUBTRACT", a, b)

    def mul(self, a, b):
        return self.math("MULTIPLY", a, b)

    def div(self, a, b):
        return self.math("DIVIDE", a, b)

    def remap(self, value, from_min, from_max, to_min=0.0, to_max=1.0, smooth=False):
        """Clamped map range; ``smooth`` gives a smoothstep."""
        node = self.node("ShaderNodeMapRange", clamp=True,
                         interpolation_type="SMOOTHSTEP" if smooth else "LINEAR")
        self.plug(node.inputs["Value"], value)
        self.plug(node.inputs["From Min"], from_min)
        self.plug(node.inputs["From Max"], from_max)
        self.plug(node.inputs["To Min"], to_min)
        self.plug(node.inputs["To Max"], to_max)
        return node.outputs[0]

    def xyz(self, x=None, y=None, z=None):
        node = self.node("ShaderNodeCombineXYZ")
        for index, value in enumerate((x, y, z)):
            self.plug(node.inputs[index], value)
        return node.outputs[0]

    def split(self, vector):
        node = self.node("ShaderNodeSeparateXYZ")
        self.plug(node.inputs[0], vector)
        return node.outputs[0], node.outputs[1], node.outputs[2]

    def vec(self, operation, a, b=None, scale=None):
        node = self.node("ShaderNodeVectorMath", operation=operation)
        self.plug(node.inputs[0], a)
        if b is not None:
            self.plug(node.inputs[1], b)
        if scale is not None:
            self.plug(node.inputs["Scale"], scale)
        return node.outputs["Value"] if operation == "LENGTH" else node.outputs["Vector"]

    def ramp(self, factor, stops):
        """Colour ramp from ``[(position, (r, g, b, a)), ...]``."""
        node = self.node("ShaderNodeValToRGB")
        elements = node.color_ramp.elements
        while len(elements) < len(stops):
            elements.new(0.5)
        for element, (position, colour) in zip(elements, stops):
            element.position = position
            element.color = colour
        self.plug(node.inputs["Fac"], factor)
        return node.outputs["Color"]
