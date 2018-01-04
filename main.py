from PIL import Image
from PIL import ImageDraw
import math
import numpy as np
import cv2
import itertools


def dopixelsneighbour(pixel1, pixel2):
    diffx = abs(pixel1[0] - pixel2[0])
    diffy = abs(pixel1[1] - pixel2[1])
    return (diffx < 2) & (diffy < 2)

def distancefromsun(pixel, angle): #
    return pixel[0] * math.cos(angle) - pixel[1] * math.sin(angle)

def distancebetweenpixels(pixel1, pixel2): #
    return math.sqrt((pixel1[0] - pixel2[0]) * (pixel1[0] - pixel2[0]) + (pixel1[1] - pixel2[1]) * (pixel1[1] - pixel2[1]))

def reversecolor(color):
    return 255 - color[0], 255 - color[1], 255 - color[2]

def anglefromtwopoints(point1, point2):
    return math.atan2(point2[1] - point1[1], point1[0] - point2[0])

def imageToData(funImage):
    if funImage.mode != "RGB":
        funImage = Image.merge("RGB", funImage.split()[:-1])

    funData = np.reshape(list(funImage.getdata()), (funImage.size[0], funImage.size[1], 3)).tolist()

    return funData

illuminationangle = 1.6
imagescale = 1

houseImage = Image.open("smallhouses.png")
houseData = imageToData(houseImage)

shadowImage = Image.open("smallshadows.png")
shadowData = imageToData(shadowImage)

#originalImage = Image.open("original.png")
emptyCanvas = Image.new("RGB", (houseImage.size[0], houseImage.size[1]), (0, 0, 0))

houses = []
shadows = []

count = 0

#1. проходим по всем пикселям и собираем их в дома (связные области черного цвета)

pixelscounted = 0
queue = []
usedpixels = []

#for x, y in itertools.product(range(0, houseImage.size[0]), range(0, houseImage.size[1])):
houseArray = np.arange(houseImage.size[0]*houseImage.size[1]).reshape(houseImage.size[0], houseImage.size[1])
for index, data in np.ndenumerate(houseArray):
    x = index[0]
    y = index[1]
    count += 1
    print(count, "of", houseImage.size[0]*houseImage.size[1])
    if (x, y) not in usedpixels:
        usedpixels.append((x, y))
        if houseData[y][x] == [0, 0, 0]:
            queue.append((x, y))
            house = []

            while len(queue) > 0:
                cur = queue.pop(0)
                house.append(cur)
                for x, y in [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]:
                    if (0 <= (cur[0] + x) < houseImage.size[0]) & (0 <= (cur[1] + y) < houseImage.size[1]) & ((cur[0] + x, cur[1] + y) not in usedpixels):
                        #if houseImage.getpixel((cur[0] + x, cur[1] + y)) == (0, 0, 0, 255):
                        if houseData[cur[1] + y][cur[0] + x] == [0, 0, 0]:
                            usedpixels.append((cur[0] + x, cur[1] + y))
                            queue.append((cur[0] + x, cur[1] + y))

            houses.append(house)

print("step 1: housalization complete")

#2. сортируем дома по самой удаленной от солнца точке
houses.sort(key=lambda x: max(map(lambda y: distancefromsun(y, illuminationangle), x)), reverse=True)

print("step 2: house sorting complete")

#3. создаем лист пикселей теней для перебора
shadowpixels = []
for x in range(0, shadowImage.size[0]):
    for y in range(0, shadowImage.size[1]):
        # pixel = shadowImage.getpixel((x, y))
        pixel = shadowData[y][x]
        if pixel == [0, 0, 0]:
            shadowpixels.append((x, y))

print("step 3: shadow pixel collecting complete")

result = {}

#4. считаем тени
for house in houses:
    # берем дом, мапим через преобразование + pi/2, смотрим макс и мин
    d1 = max(zip(house, house), key=lambda x: distancefromsun(x[1], illuminationangle + math.pi / 2))[0]
    d2 = min(zip(house, house), key=lambda x: distancefromsun(x[1], illuminationangle + math.pi / 2))[0]

    currentshadowpixels = []
    for pixel in shadowpixels:
        angle1 = anglefromtwopoints(pixel, d1)
        angle2 = anglefromtwopoints(pixel, d2)
        if ((angle2 - angle1) % (2 * math.pi)) > math.pi:
            angle1, angle2 = angle2, angle1
        if angle2 < angle1:
            angle2 += 2 * math.pi

        if angle2 >= illuminationangle >= angle1:
            currentshadowpixels.append(pixel)
            #emptyCanvas.putpixel(pixel, (255, 0, 0))

    for pixel in currentshadowpixels:
        shadowpixels.remove(pixel)

    result[tuple(house[0])] = [house, currentshadowpixels] #словарь: ключи - верхние левые пиксели, значения - пары: пиксели дома, пиксели тени


d = ImageDraw.Draw(emptyCanvas)
count = 0
step = 255 // len(result)
for key in result:
    for s in result[key][1]:
        emptyCanvas.putpixel(s, (255 - step * count, step * count, 255 - step * count))
    for h in result[key][0]:
        emptyCanvas.putpixel(h, (step * count, 255 - step * count, step * count))

    farthestHousePix = max(result[key][0], key=lambda x: distancefromsun(x, illuminationangle))
    if len(result[key][1]) != 0:#у здания есть тень
        farthestShadowPix = max(result[key][1], key=lambda x: distancefromsun(x, illuminationangle))

        height = distancebetweenpixels(farthestShadowPix, farthestHousePix) * imagescale
    else:#у здания нет тени
        height = 0

    d.text(key, str(round(height, 2)))
    count += 1
print(len(houses))

emptyCanvas.show()
#originalImage.paste(emptyCanvas, (0, 0), emptyCanvas)
#originalImage.show()