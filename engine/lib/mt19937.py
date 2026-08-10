# github.com/yinengy/Mersenne-Twister-in-Python/blob/master/RandomClass.py
from core import *

class Random():
    def __init__(self, c_seed: int=0):
        # MT19937
        (self.w, self.n, self.m, self.r) = (32, 624, 397, 31)
        self.a = 0x9908B0DF
        (self.u, self.d) = (11, 0xFFFFFFFF)
        (self.s, self.b) = (7, 0x9D2C5680)
        (self.t, self.c) = (15, 0xEFC60000)
        self.l = 18
        self.f = 1812433253
        # make a arry to store the state of the generator
        self.MT = [0 for _ in range(self.n)]
        self.index = self.n+1
        self.lower_mask = 0x7FFFFFFF
        self.upper_mask = 0x80000000
        # inital the seed
        self.c_seed = c_seed
        self.seed(c_seed)

    def seed(self, num: int):
        """initialize the generator from a seed"""
        self.MT[0] = num
        self.index = self.n
        for i in range(1, self.n):
            temp = self.f * (self.MT[i-1] ^ (self.MT[i-1] >> (self.w-2))) + i
            self.MT[i] = temp & 0xffffffff

    def twist(self):
        """ Generate the next n values from the series x_i"""
        for i in range(0, self.n):
            x = (self.MT[i] & self.upper_mask) + \
                (self.MT[(i+1) % self.n] & self.lower_mask)
            xA = x >> 1
            if (x % 2) != 0:
                xA = xA ^ self.a
            self.MT[i] = self.MT[(i + self.m) % self.n] ^ xA
        self.index = 0

    def extract_number(self):
        """ Extract a tempered value based on MT[index]
            calling twist() every n numbers
        """
        if self.index >= self.n:
            self.twist()

        y = self.MT[self.index]
        y = y ^ ((y >> self.u) & self.d)
        y = y ^ ((y << self.s) & self.b)
        y = y ^ ((y << self.t) & self.c)
        y = y ^ (y >> self.l)

        self.index += 1
        return y & 0xffffffff

    def random(self):
        """ return uniform ditribution in [0,1) """
        # a = (self.extract_number() / 10**8) % 1
        # return float('%.08f' % a)
        # Deliberately not used to pick indices. Scaling this float was how the old randint worked,
        # and it is why this generator produced a different game from numpy off the same seed even
        # though the word stream was already identical. Bounded integers come off the raw words.
        return self.extract_number() / 4294967296  # which is 2**w

    def GetState(self):
        """A snapshot of the generator position, for the debug undo.

        Mirrors `numpy.random.get_state()`, so `Random.PushState` can treat the two backends the
        same way. The word list is copied, otherwise the snapshot moves as the generator runs.
        """
        return (self.MT[:], self.index)

    def SetState(self, state) -> None:
        words, index = state
        assert len(words) == self.n, f"state needs {self.n} words, got {len(words)}"
        assert 0 <= index <= self.n, f"state index out of range: {index}"
        self.MT = words[:]
        self.index = index

    def randbelow(self, n: int) -> int:
        """ return random int in [0,n) the way numpy does it

        Masked rejection, matching numpy's `random_interval`: mask down to the next power of two
        and redraw while the value is out of range. Rejection is the point. It is what makes the
        draw uniform without a modulo bias, and it means an operation does not always consume the
        same number of words, so no float-scaling shortcut can imitate it.
        """
        assert n >= 1, f"n must be at least 1, got {n}"

        mask = n - 1
        mask |= mask >> 1
        mask |= mask >> 2
        mask |= mask >> 4
        mask |= mask >> 8
        mask |= mask >> 16

        while True:
            value = self.extract_number() & mask
            if value < n:
                return value

    def randint(self, a: int, b: int):
        """ return random int in [a,b) """
        return a + self.randbelow(b - a)

    def shuffle(self, X: List[Any]) -> None:
        """ shuffle the sequence, matching numpy.random.shuffle

        Fisher-Yates walking down, `len - 1` draws, which is numpy's exact algorithm. The previous
        version made `10 * len` random transpositions: a fair enough shuffle, but a different
        sequence and 20x the draws, so it desynchronised every later draw as well.
        """
        for i in range(len(X) - 1, 0, -1):
            j = self.randbelow(i + 1)
            X[i], X[j] = X[j], X[i]

    def choice(self, X: List[Any], replace: bool=True, size: int=1):
        """ choose `size` elements, matching numpy.random.choice

        `replace=False` is a full shuffle truncated to `size`, because that is what numpy does
        (`permutation(n)[:size]`). Drawing `size` items directly gives an equally fair sample but
        spends `size` draws instead of `len - 1`, which moves every later draw in the game.
        """
        newX = list(X)
        if replace:
            # Not reached from the engine: `Random.RandomChoice2` only ever asks for replace=False,
            # and single draws go through `choice_one`. Kept because it is part of the reference
            # implementation this file came from, and pinned against numpy in
            # test_rng_numpy_parity so an unused branch cannot quietly become a wrong one.
            return [newX[self.randbelow(len(newX))] for _ in range(size)]
        self.shuffle(newX)
        return newX[:size]

    def choice_one(self, X: Sequence[Any]):
        """ choice an element randomly in the sequence 
            size: the number of element to be chosen
        """
        newX = list(X)
        return newX[self.randint(0, len(newX))]

    # def bern(self, p):
    #     """ generate a Bernoulli Random Variable
    #         p: the probability of True
    #     """
    #     return self.random() <= p

    # def binomial(self, n, p):
    #     """ generate a Binomial Random Variable
    #         n: total times
    #         p: probability of success
    #     """
    #     a = [self.bern(p) for n in range(n)]
    #     return a.count(True)

    # def geometric(self, p):
    #     """ generate a Geometric Random Variable
    #         p: probability of success
    #     """
    #     u = self.random()
    #     b = 0
    #     k = 1
    #     while b < u:
    #         b += (1-p)**(k-1)*p
    #         k += 1

    #     return k - 1