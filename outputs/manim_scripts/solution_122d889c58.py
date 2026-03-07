from manim import *

class MathSolution(Scene):
    def construct(self):
        title = Title(r"Algebra: $x^2 - 3x + 5$")
        self.play(Write(title))
        self.wait(1)

        step1 = MathTex(r"Given: x^2 - 3x + 5")
        self.play(FadeIn(step1))
        self.wait(1)

        step2 = MathTex(r"This is a quadratic equation in the form of $ax^2 + bx + c$")
        self.play(ReplacementTransform(step1, step2))
        self.wait(1)

        step3 = MathTex(r"Where $a = 1$, $b = -3$, and $c = 5$")
        self.play(ReplacementTransform(step2, step3))
        self.wait(1)

        step4 = MathTex(r"To find the solution, we can use the quadratic formula: $x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}$")
        self.play(ReplacementTransform(step3, step4))
        self.wait(1)

        step5 = MathTex(r"Substituting the values of $a$, $b$, and $c$ into the quadratic formula: $x = \frac{-(-3) \pm \sqrt{(-3)^2 - 4(1)(5)}}{2(1)}$")
        self.play(ReplacementTransform(step4, step5))
        self.wait(1)

        step6 = MathTex(r"x = \frac{3 \pm \sqrt{9 - 20}}{2}")
        self.play(ReplacementTransform(step5, step6))
        self.wait(1)

        step7 = MathTex(r"x = \frac{3 \pm \sqrt{-11}}{2}")
        self.play(ReplacementTransform(step6, step7))
        self.wait(1)

        step8 = MathTex(r"The equation has no real solutions, but it has complex solutions: $x = \frac{3 \pm i\sqrt{11}}{2}$")
        self.play(ReplacementTransform(step7, step8))
        self.wait(1)

        answer = MathTex(r"x = \frac{3 \pm i\sqrt{11}}{2}", color=GREEN)
        self.play(ReplacementTransform(step8, answer))
        self.wait(2)