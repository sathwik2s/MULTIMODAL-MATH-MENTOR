from manim import *

class TestScene(Scene):
    def construct(self):
        title = Text("Test", font_size=40).to_edge(UP)
        self.play(Write(title))
        eq = MathTex(r"E = mc^2", font_size=36, color=BLUE)
        self.play(FadeIn(eq))
        self.wait(1)
