#include <stdlib.h>
#include <string.h>

#define BUCKETS 101

typedef struct Entry {
  char *value;
  int row;
  int type;
  struct Entry *next;
} Entry;

typedef struct {
  Entry *buckets[BUCKETS];
  int size;
} SymbolTable;

static unsigned hash(const char *value) {
  unsigned sum = 0;
  while (*value) {
    sum += (unsigned char)*value;
    ++value;
  }
  return sum % BUCKETS;
}

SymbolTable *st_create(void) { return calloc(1, sizeof(SymbolTable)); }

int st_lookup(const SymbolTable *table, const char *value) {
  unsigned bucket = hash(value);
  for (Entry *e = table->buckets[bucket]; e; e = e->next)
    if (strcmp(e->value, value) == 0)
      return (int)bucket;
  return -1;
}

int st_position(const SymbolTable *table, const char *value) {
  int position = 0;
  for (Entry *e = table->buckets[hash(value)]; e; e = e->next) {
    if (strcmp(e->value, value) == 0)
      return position;
    ++position;
  }
  return -1;
}

int st_insert(SymbolTable *table, const char *value, int type) {
  int existing = st_lookup(table, value);
  if (existing >= 0)
    return existing;
  Entry *e = malloc(sizeof(*e));
  if (!e)
    return -1;
  e->value = malloc(strlen(value) + 1);
  if (!e->value) {
    free(e);
    return -1;
  }
  strcpy(e->value, value);
  unsigned bucket = hash(value);
  e->type = type;
  e->row = table->size++;
  e->next = NULL;
  Entry **tail = &table->buckets[bucket];
  while (*tail)
    tail = &(*tail)->next;
  *tail = e;
  return (int)bucket;
}

int st_size(const SymbolTable *table) { return table->size; }

const char *st_value(const SymbolTable *table, int row) {
  for (unsigned b = 0; b < BUCKETS; ++b)
    for (Entry *e = table->buckets[b]; e; e = e->next)
      if (e->row == row)
        return e->value;
  return NULL;
}

int st_type(const SymbolTable *table, int row) {
  for (unsigned b = 0; b < BUCKETS; ++b)
    for (Entry *e = table->buckets[b]; e; e = e->next)
      if (e->row == row)
        return e->type;
  return -1;
}

int st_bucket(const SymbolTable *table, int row) {
  for (unsigned b = 0; b < BUCKETS; ++b)
    for (Entry *e = table->buckets[b]; e; e = e->next)
      if (e->row == row)
        return (int)b;
  return -1;
}

void st_destroy(SymbolTable *table) {
  if (!table)
    return;
  for (unsigned b = 0; b < BUCKETS; ++b) {
    Entry *e = table->buckets[b];
    while (e) {
      Entry *next = e->next;
      free(e->value);
      free(e);
      e = next;
    }
  }
  free(table);
}
