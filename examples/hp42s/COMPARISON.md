# HP-42S Function Plotter — MGRAPH vs KGRAPH

Two implementations of the same program: plot a user-defined function on the
HP-42S 131×16 pixel display.

| | MGRAPH (MCP-assisted) | KGRAPH (knowledge-based) |
|---|---|---|
| **Source** | hp42s-prog-en.pdf via calculator-rag | General HP-42S knowledge |
| **Range variables** | Named (`XMIN`, `XMAX`, `YMIN`, `YMAX`) | Numbered (`R00`–`R03`) |
| **Axis drawing** | Yes — `XAXIS` + `YAXIS` subroutines | No |
| **User control** | Flag 00/01 suppress each axis | None |
| **Registers used** | R10–R15 | R04–R07 |
| **Program size** | ~90 instructions | ~50 instructions |
| **x exposed to F** | Both X-register and named var `"X"` | X-register only |

---

## What the MCP added

The calculator-rag search found the HP-42S manual's PLOT program (hp42s-prog-en.pdf).
That source contributed three concrete details not easily recalled from memory:

1. **Display dimensions confirmed as 131 × 16 pixels.**  
   The manual explicitly says "16 rows in the display" — easy to mis-remember as 7 or 8
   (the number of text lines the display *normally* shows).

2. **PLOT program structure** — pre-computing `x_step` and `y_range` before the loop,
   then calling a named subroutine `"F"` for the function, matches the manual's idiom.
   The knowledge version uses the same structure because it is correct practice, but the
   MCP confirmed it as the documented convention rather than an assumption.

3. **Axis drawing subroutines with flag control** (`FS? 00 / XEQ "XAXIS"`, etc.).  
   The manual says "If flag 00 is clear, draw the x-axis." The MCP result surfaced this
   feature; the knowledge version omits it entirely.

---

## Algorithm (identical in both)

```
x_step = (Xmax - Xmin) / 130
y_range = Ymax - Ymin

for col = 1 to 131:
    x  = Xmin + (col - 1) * x_step
    y  = F(x)
    row = 16 - floor((y - Ymin) / y_range * 15 + 0.5)
    if 1 <= row <= 16:
        PIXEL(row, col)
```

`row = 1` → top of screen (y = Ymax)  
`row = 16` → bottom of screen (y = Ymin)  
The `+ 0.5` before `IP` rounds to the nearest pixel rather than always flooring.

---

## HP-42S coding notes

### PIXEL operand order
`PIXEL` expects **Y-register = row**, **X-register = column** (confirmed by the manual).  
Both programs follow this pattern:
```
RCL row_reg    ; row → X, then becomes Y after next push
RCL col_reg    ; col → X; row now in Y
PIXEL
```

### Conditional-test direction
HP-42S conditional tests **SKIP the immediately following instruction when TRUE**.  
This inverts the intuitive reading. Both programs use the two-GTO pattern:

```
X<Y?           ; if X < Y (TRUE) → skip GTO A, reach GTO B
GTO A          ; reached when condition FALSE
GTO B          ; reached when condition TRUE
LBL A
```

### Why saving `row` to a register matters
After computing `row` the bounds-check code pushes additional constants (`1`, `16`)
onto the stack. Without `STO 07` (KGRAPH) / `STO 13` (MGRAPH) immediately after
the `row` computation, the value would be buried under those constants and unavailable
at the `PIXEL` call.

---

## How to run (Free42 or physical HP-42S)

1. Enter the program via the keyboard or import the file.
2. Set the range (example — plot sin(x) from -π to +π):
   ```
   -3.14159  STO 00    (KGRAPH) or  STO "XMIN"  (MGRAPH)
    3.14159  STO 01                  STO "XMAX"
   -1.5      STO 02                  STO "YMIN"
    1.5      STO 03                  STO "YMAX"
   ```
3. Ensure `LBL "F"` contains your function (default: `SIN`).
4. `XEQ "KGRAPH"` or `XEQ "MGRAPH"`.
