'*.tar.gz' | head -n 1)
    check "в архиве app 07.log" in_archive "$arch" "app 07.log"
    check "в архиве app 02.log" in_archive "$arch" "app 02.log"
    check "в архиве app 09.log" in_archive "$arch" "app 09.log"
    check "app 07.log удалён" test ! -e "$log/app 07.log"
    check "app 02.log удалён" test ! -e "$log/app 02.log"
    check "app 09.log удалён" test ! -e "$log/app 09.log"
    check "новый app 01.log на месте" test -e "$log/app 01.log"
}

# Тест 4: проверяет защиту от потери данных. Если архив не создался (нет прав),
# скрипт должен вернуть ошибку и не удалять оригиналы.
test_archive_failure() {
    if [ "$(id -u)" -eq 0 ]; then
        echo "  [SKIP] от root нельзя сделать папку недоступной для записи"
        return
    fi
    local d="$SANDBOX/t4"
    local log="$d/log" bak="$d/backup"
    mkdir -p "$bak"
    make_logs "$log" 12
    chmod 555 "$bak"  # Запрещаем запись в папку бэкапов.

    echo "  [INFO] Условия: логи 600 МБ, ёмкость 700 МБ (85%), порог 70%. Папка бэкапов недоступна для записи"
    run_backup "$log" "$bak" 700 70
    chmod 755 "$bak"  # Возвращаем права, чтобы тест не сломал песочницу.

    check "завершение с ошибкой (код не 0)" test "$RC" -ne 0
    check "все 12 файлов на месте" test "$(count_files "$log")" -eq 12
}

# Тест 5: проверяет, что скрипт правильно реагирует на изменение порога (60% вместо 70%).
test_custom_threshold() {
    local d="$SANDBOX/t5"
    local log="$d/log" bak="$d/backup"
    mkdir -p "$bak"
    make_logs "$log" 12

    echo "  [INFO] Условия: логи 600 МБ, ёмкость 700 МБ (85%), порог 60%"
    run_backup "$log" "$bak" 700 60

    local arch
    arch=$(find "$bak" -name '*.tar.gz' | head -n 1)
    check "успешное завершение (код 0)" test "$RC" -eq 0
    check "в архиве 4 файла" test "$(tar -tzf "$arch" | wc -l)" -eq 4
    check "в /log осталось 8 файлов" test "$(count_files "$log")" -eq 8
    check "заполнение стало <= 60%" \
        test "$(used_bytes "$log")" -le $(( 700 * 1024 * 1024 * 60 / 100 ))
}

# Тест 6: проверяет, что скрипт не падает, а выдает ошибку при неверных аргументах.
test_bad_args() {
    local d="$SANDBOX/t6"
    local log="$d/log" bak="$d/backup"
    mkdir -p "$bak"
    make_logs "$log" 12

    echo "  [INFO] Условия: проверка обработки неверных аргументов"
    
    OUT=$(BACKUP_DIR="$bak" "$BACKUP_SH" 2>&1); RC=$?
    check "нет аргумента -> ошибка ввода (код 1)" test "$RC" -eq 1

    OUT=$(BACKUP_DIR="$bak" "$BACKUP_SH" "$d/nope" 70 2>&1); RC=$?
    check "нет папки -> ошибка пути (код 1)" test "$RC" -eq 1

    OUT=$(LOG_CAPACITY=$(( 700 * 1024 * 1024 )) BACKUP_DIR="$bak" \
          "$BACKUP_SH" "$log" abc 2>&1); RC=$?
    check "порог 'abc' -> ошибка формата (код 1)" test "$RC" -eq 1

    check "в /log все 12 файлов" test "$(count_files "$log")" -eq 12
    check "архив не создан" test -z "$(find "$bak" -name '*.tar.gz')"
}

# Запуск тестов.
echo "Тестируем: $BACKUP_SH"
echo "Песочница: $SANDBOX"
echo

echo "== Тест 1: Заполнение ниже порога (ничего не трогаем)"
test_below_threshold
echo

echo "== Тест 2: Заполнение выше порога (архивируем и удаляем)"
test_above_threshold
echo

echo "== Тест 3: Архивируем именно самые старые файлы (сортировка по mtime)"
test_oldest_first
echo

echo "== Тест 4: Сбой архивации (защита от потери данных)"
test_archive_failure
echo

echo "== Тест 5: Свой порог 60% (проверка аргумента)"
test_custom_threshold
echo

echo "== Тест 6: Кривые аргументы (валидация ввода)"
test_bad_args
echo

# Итог. Если $FAIL равно 0, скрипт завершится с кодом 0 (успех).
echo "Итого: пройдено $PASS, провалено $FAIL"
[ "$FAIL" -eq 0 ]
