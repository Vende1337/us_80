import base64
import io
import matplotlib.pyplot as plt
from django.shortcuts import render
from django.core.files.storage import FileSystemStorage
import decimal
from decimal import Decimal
import matplotlib.pyplot as plt
import math
import os
from django.contrib.staticfiles import storage
from django.http import FileResponse

import us_80.settings


decimal.getcontext().prec = 100

storage = storage.StaticFilesStorage()


def main(request):
    """Основная функция."""
    context = {}
    if request.method == 'POST' and request.FILES['myfile']:
        myfile = request.FILES['myfile']
        fs = FileSystemStorage()
        filename = fs.save(myfile.name, myfile)

        def solution(z, T, S):
            """Функция расчета условной плотности."""
            P = Decimal(1.009449e4)*z+Decimal(2.13858e-2)*z**2

            res = Decimal(0.01)*abs(Decimal(2815.2)-Decimal(7.35)*T-Decimal(0.469)*T**2+(Decimal(80.2)-Decimal(0.2)*T)
                                    * (Decimal(S)-Decimal(35))) + Decimal(4.6) * Decimal(10 ** (-7))*Decimal(P)
            return res

        # Создаем массивы для работы с данными.
        z_list = []
        list_of_qt = []
        list_of_vt = []
        list_of_vtp = []
        list_of_D = []
        list_of_d = []
        zero_st_v = []
        zero_st_u = []
        zero_st_c = []

        # Читаем файл и заполяем массив глубин.
        with open(fs.path(filename), 'r') as file:
            lines = file.readlines()
        for line in lines:
            values = line.strip().split()
            z_list.append(values[0])
        count_of_st = (len(values)-1)//2

        # Создаем массивы для каждой из станций.
        for _ in range(count_of_st):
            list_of_qt.append([])
            list_of_vt.append([])
            list_of_vtp.append([])
            list_of_D.append([])
            list_of_d.append([])
        k = -1
        # Рассчитываем удельную плотность, переводим ее в условный удельный объем
        # рассчитываем Сред. Vpts * Δp
        for line in lines:
            values = line.strip().split()
            z = values[0]
            k2 = 2
            for i in range(2, len(values), 2):
                pre_res = round(solution(Decimal(z), Decimal(
                    values[i-1]), Decimal(values[i])), 2)

                list_of_qt[i-k2].append(float(pre_res))
                list_of_vt[i -
                           k2].append(round((10**6/(float(pre_res)+10**3))-900, 2))

                if k < len(z_list)-1 and len(list_of_vt[i-k2]) > 1:
                    list_of_vtp[i-k2].append(round((((10**6/(float(pre_res)+10**3))-900 +
                                                     list_of_vt[i-k2][k])/2)*abs(int(z_list[k+1])-int(z_list[k])), 2))
                k2 += 1
            k += 1
        p = 0
        # Рассчитываем динамические глубины и высоты.
        for i in range(count_of_st):
            for q in range(len(z_list)):
                if q == 0:
                    p = 0
                else:
                    p += list_of_vtp[i][q-1]
                list_of_D[i].append(round(p, 2))
            p = 0
            D = list_of_D[i][len(z_list)-1]
            for q in range(len(z_list)):
                if q != len(z_list)-1:
                    list_of_d[i].append(round(D, 2))
                    D -= list_of_vtp[i][q]
                else:
                    list_of_d[i].append(0)

        # Рассчитываем коэффициенты.
        M1 = 0.01/(2*7.29**(-5)*(1.2*0.621371)*math.sin(math.radians(55)))
        M2 = 0.01/(2*7.29**(-5)*(0.9*0.621371)*math.sin(math.radians(55)))

        # Рассчитываем составляющие геострофического течения.
        for i in range(len(z_list)):
            zero_st_v.append(
                round((abs(list_of_d[2][i]-list_of_d[0][i])*M1)/10, 2))
            zero_st_u.append(
                round((abs(list_of_d[3][i]-list_of_d[1][i])*M2)/10, 2))
            zero_st_c.append(
                round(math.sqrt(zero_st_v[i]**2+zero_st_u[i]**2), 2))

        # Создаем и заполняем новый файл используя полученные данные.
        with storage.open("new_file.txt", "w+") as f:
            f.write("z.m  v cm/c    u cm/c   c cm/c\n")
            for i in range(len(z_list)):
                f.write(
                    f"{z_list[i]}    {zero_st_v[i]}    {zero_st_u[i]}    {zero_st_c[i]}\n")
        with storage.open("new_file.txt", "r") as f:
            content = f.read()
        context['content'] = content
        # Строим профиль вертикального распределения составляющих.
        fig, ax = plt.subplots(figsize=(6, 12))

        ax.set_ylabel('Глубина (м)')
        ax.set_xlabel('Скорость (см/с)')
        ax.set_title(
            f'Профиль вертикального распределения\n'
            'составляющих геострофического течения.')

        ax.plot(zero_st_v, z_list, label='V-компонента', color='blue')
        ax.plot(zero_st_u, z_list, label='U-компонента', color='red')
        ax.plot(zero_st_c, z_list, label='C-компонента', color='green')
        ax.invert_yaxis()
        ax.legend(loc='lower right', fontsize='large')

        img_data = io.BytesIO()
        plt.savefig(img_data, format='png')
        img_data.seek(0)

        graphic = base64.b64encode(img_data.getvalue()).decode()

        plt.close()
        context['graphic'] = graphic

    return render(request, 'index.html', context)


def send(response):
    """Функция для загрузки полученного файла."""
    file_path = os.path.join(us_80.settings.STATIC_ROOT, "new_file.txt")
    file = open(file_path, 'rb')
    response = FileResponse(file)
    response['Content-Disposition'] = 'attachment; filename="new_file.txt"'
    return response
