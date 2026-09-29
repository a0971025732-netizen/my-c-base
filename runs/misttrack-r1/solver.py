import re

VOCAB = {
    "seventeen":17,"eighteen":18,"nineteen":19,"fourteen":14,"thirteen":13,"sixteen":16,"fifteen":15,
    "eleven":11,"twelve":12,"twenty":20,"thirty":30,"forty":40,"fifty":50,"sixty":60,"seventy":70,
    "eighty":80,"ninety":90,"seven":7,"eight":8,"three":3,"nine":9,"four":4,"five":5,"zero":0,
    "ten":10,"one":1,"two":2,"six":6,
}
ORDER = sorted(VOCAB, key=len, reverse=True)  # longest match first

def solve(challenge: str):
    s = challenge.lower()
    mult = ("*" in s) or ("times" in s) or ("multipl" in s) or ("product" in s)
    letters = re.sub("[^a-z]", "", s)
    sub = any(w in letters for w in ["loses","lose","reduce","decreas","slow","drops","minus","subtract","lost"])
    toks = []
    i = 0
    while i < len(letters):
        m = None
        for w in ORDER:
            if letters.startswith(w, i):
                m = w; break
        if m:
            toks.append(VOCAB[m]); i += len(m)
        else:
            i += 1
    # fold tens + unit (e.g. twenty three -> 23)
    nums = []
    j = 0
    while j < len(toks):
        v = toks[j]
        if v in (20,30,40,50,60,70,80,90) and j+1 < len(toks) and 1 <= toks[j+1] <= 9:
            nums.append(v + toks[j+1]); j += 2
        else:
            nums.append(v); j += 1
    if len(nums) < 2:
        return None, (nums, mult, sub)
    a, b = nums[0], nums[1]
    r = a*b if mult else (a-b if sub else a+b)
    return round(float(r), 2), (nums, mult, sub)

if __name__ == "__main__":
    tests = [
        ("ThIs] LoO-bS tErr Um^ ClAw| FoR~cE Is TwEnTy {ThReE} NeW\toNs- AnD Um] AnO-tHeR ClAw^ AdDs SeVeNtEeN NeW<toNs, WhAt Is ToTaL FoR}cE?", 40),
        ("A] L oO^bS tE-r L ooObSssTeR S^wI mS[ aT/ tH iR tY T wO cE nT iMeRs PeR/ sE cOnD- aNd^ aC cE lErA tEs] bY/ eI gH t, wH aT s] tH e N eW- vE lO cItY?", 40),
        ("A] LlOoBbStTeRr ~ ClAw^ FoRcE iS| TwEnTy FiVe { NeWtOoNs } * TwO < LoObBsTtErS > HoW MuCh ToTaL FoRcE?", 50),
        ("Lo]b-StEr S^wImS um, LiKe, AnD ClAw ExErTs TwEnTy FiVe NoOoToNs~ OtH eR ClAw A]dDs FiFtEeN NoOtOnS - WhAt Is ToTaL FoR cE?", 40),
        ("A] LoOoBbSsStTeErR- ClAw] FoRcE^ iS/ ThIrTy FiVrEe NeWtOoNs ~+~ ThE/ OtHeR- ClAaW{ hAs } TwEeLvE, UmMm WhAt Is ToTaL- FoRcE?", 47),
        ("] A lO^bSt-Er S[wImS\\ aT] TrWeNtY~ ThHrEe{ mE]tE|rS /pEr ~SeCoNd - BuT }LoOoSsEe[ SeVeN< mE}tErS, WhHaT'S^ ThE NeW~ SpEeD?", 16),
        ("A] Lo bS-tEr LoO bSsTeR ClAw] FoRcE Is ThIrTy TwO NeWtOnS ~ AnD OtHeR ClAw HaS FoUrTeEn NeWtOnS / Um, WhAt Is ToTaL FoRcE?", 46),
        ("A] L oObBsStTeEr ]hAaS^ cLlAaWw F oOrRcCeE ]tW/eNnTy] tHrReEe^ nEeWwToOnNs, uMm ]dUrRiInG~ aN tErR iToRy fIiGhT^ iT/ lOoSsEs ]sEeVeEn~ dUe^ tO/ wAaTeEr] pReSsSuUrEe, wH-aT] iS^ tHe/ rEeMaAiInNiNg ]fOoRrCeEe?", 16),
        ("A] LoOobssTtErr }ClAw^ FoRcE Is/ ThIrTy TwO + AnD ]AnOtHeR }Lo.bS tErR ClAw^ FoRcE Is/ FoUrTeEn <NeWtOnS, WhAtS ThE/ ToTaL- FoRcE? umm", 46),
        ("A] Lo^bSt-ErS ] lOoObSsTtEeR sWiMmS[ iN tHe ] sAlInE ~ cUrReNt, tHe Ir ClAwS| pRoDuCe ] aN eXpErImEnTaL / fOrCe, tHe Re|SeArChErS NoTe ] tHe ] sWiMmInG veLoOwciTyyy iS ThIrTy TwO, aNd] tHe ClAw FoRcE iNcReAsEs < bY > FoUrTeEn, WhAt Is ] tHe ToTaL | cLaW FoRcE?", 46),
        ("U m] L oO bS sStEr- sS ^wI tH- cLaW] fO rCe^ oF- tHiR tY] tWo/ nEwToNs- ,] cOlL iS. deS ^wI tH- aN oThEr] pU sH iN g- sIxT eEn/ nEwToNs- ,] wHaT/ iS- tHe] tOtA l- fO rCe^?", 48),
        ("A] lO-bS tEr^ lxOoobsssStEr ]eX^eRtS/ tH-iR tY fIvE {nEeWoOtOnSs} - oF ] cLaW| fOrCe, aNd] aNoThEr^ lO.oB sT er ]aDdS- tW/eLvE <nEeWoOtOnSs>, wHaT] iS^ tHe] ToTaL| fOrCe?", 47),
        ("A] lOoO bS tTeErr S^wImS/ wItH vEeLlOoOcCiTyY tW]eN tY fOuR mE^tErS pEr/ sEcOnD ~ BuT[ aN oThErr lO.o bS tTeEr ClAwW rEdDuCeSs iT bY sIx, WhAt/ Is] ThE nEw^ vElOoCiTy?", 18),
        ("A] Lo bS tEr ClAw FoRcE Is ThIrTy TwO NeWtOnS AnD OtHeR ClAw HaS FoUrTeEn", 46),
    ]
    ok = 0
    for chal, exp in tests:
        got, dbg = solve(chal)
        flag = "OK" if got == exp else "**FAIL**"
        if got == exp: ok += 1
        print(f"{flag} exp={exp} got={got} nums={dbg[0]} mult={dbg[1]} sub={dbg[2]}")
    print(f"\n{ok}/{len(tests)} passed")
