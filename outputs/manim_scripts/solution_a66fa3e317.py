from manim import *

class MathSolution(Scene):
    def construct(self):
        title = Text("Algebra Problem: (r-a)(r-b) = λ(a-b) + S = 0")
        self.play(Write(title))
        self.wait(1)
        self.play(FadeOut(title))

        step1 = MathTex(r"(r-a)(r-b) = \lambda(a-b) + S = 0")
        self.play(Write(step1))
        self.wait(1)

        step2 = MathTex(r"(r-a)(r-b) = 0")
        self.play(Transform(step1, step2))
        self.wait(1)

        step3 = MathTex(r"r = a \text{ or } r = b")
        self.play(ReplacementTransform(step1, step3))
        self.wait(1)

        step4 = MathTex(r"(x-a)^3 = ?")
        self.play(Write(step4))
        self.wait(1)
        self.play(FadeOut(step3))

        step5 = MathTex(r"(x-a)^3 = (x-r)^3")
        self.play(ReplacementTransform(step4, step5))
        self.wait(1)

        step6 = MathTex(r"(x-a)^3 = (x-a)^3")
        self.play(ReplacementTransform(step5, step6))
        self.wait(1)

        answer = MathTex(r"(x-a)^3 = \boxed{(x-a)^3}", color=GREEN)
        self.play(ReplacementTransform(step6, answer))
        self.wait(2)