from PIL import Image, ImageDraw

def pictogram(key):
    # Original, dependency-free line drawings on a 64 x 64 transparent canvas.
    im = Image.new('RGBA', (64, 64))
    d = ImageDraw.Draw(im)
    def line(points, width=5):
        d.line(points, fill='white', width=width, joint='curve')
    def box(b):
        d.rounded_rectangle(b, radius=3, outline='white', width=4)
    def circle(x,y,r):
        d.ellipse((x-r,y-r,x+r,y+r), outline='white', width=4)
    if key == 1:  # Car
        line([(7,39),(7,27),(16,24),(23,12),(43,12),(51,24),(57,27),(57,39),(7,39)])
        line([(17,24),(50,24)],3); circle(17,42,5); circle(47,42,5)
    elif key == 2:  # Lightning
        d.polygon([(35,3),(12,36),(29,36),(25,61),(53,24),(36,24)],fill='white')
    elif key == 3:  # Suspension spring
        line([(20,6),(44,6)]); line([(32,6),(32,13)],3)
        line([(32,13),(18,20),(46,28),(18,36),(46,44),(32,51)])
        line([(32,51),(32,58)],3); line([(20,58),(44,58)])
    elif key == 4:  # Chip
        box((17,17,47,47)); box((25,25,39,39))
        for t in (22,32,42):
            line([(t,7),(t,17)],3); line([(t,47),(t,57)],3)
            line([(7,t),(17,t)],3); line([(47,t),(57,t)],3)
    elif key == 5:  # Robot arm
        line([(9,56),(55,56)]); box((22,44,42,54))
        line([(32,44),(17,28),(38,10),(52,23)],7)
        circle(17,28,5); circle(38,10,5); line([(47,24),(53,30),(59,24)],3)
    elif key == 6:  # Hexagonal nut
        pts=[(32,5),(55,18),(55,46),(32,59),(9,46),(9,18),(32,5)]
        line(pts,5); circle(32,32,12)
    elif key == 7:  # Inspection magnifier
        circle(25,25,17); line([(38,38),(56,56)],7)
        line([(16,25),(23,32),(34,19)],4)
    elif key == 8:  # Checkered flag
        line([(12,58),(12,6)],4); box((13,7,55,39))
        for y in range(3):
            for x in range(4):
                if (x+y)%2==0: d.rectangle((15+x*10,9+y*10,24+x*10,18+y*10),fill='white')
    elif key == 9:  # Laboratory flask
        line([(23,6),(41,6)]); line([(26,6),(26,25),(10,51),(12,57),(52,57),(54,51),(38,25),(38,6)])
        line([(18,40),(46,40)],3); circle(32,47,3)
    else:
        line([(23,19),(27,12),(39,12),(44,21),(32,33),(32,40)]); circle(32,51,2)
    return im


