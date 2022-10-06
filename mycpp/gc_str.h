#ifndef STR_TYPES_H
#define STR_TYPES_H

template <typename T>
class List;

class Str : public Obj {
 public:
  // Don't call this directly.  Call AllocStr() instead, which calls this.
  Str() : Obj(Tag::Opaque, kZeroMask, 0) {
  }

  char* data() {
    return data_;
  }

  void SetObjLenFromStrLen(int str_len);

  // Useful for getcwd() + PATH_MAX, gethostname() + HOSTNAME_MAX, etc.
  void SetObjLenFromC() {
    SetObjLenFromStrLen(strlen(data_));
  }

  Str* index_(int i);

  int find(Str* needle, int pos = 0);
  int rfind(Str* needle);

  Str* slice(int begin);
  Str* slice(int begin, int end);

  Str* strip();
  // Used for CommandSub in osh/cmd_exec.py
  Str* rstrip(Str* chars);
  Str* rstrip();

  Str* lstrip(Str* chars);
  Str* lstrip();

  Str* ljust(int width, Str* fillchar);
  Str* rjust(int width, Str* fillchar);

  bool startswith(Str* s);
  bool endswith(Str* s);

  Str* replace(Str* old, Str* new_str);
  Str* join(List<Str*>* items);

  List<Str*>* split(Str* sep);
  List<Str*>* splitlines(bool keep);

  bool isdigit();
  bool isalpha();
  bool isupper();

  Str* upper();
  Str* lower();

  // Other options for fast comparison / hashing / string interning:
  // - unique_id_: an index into intern table.  I don't think this works unless
  //   you want to deal with rehashing all strings when the set grows.
  //   - although note that the JVM has -XX:StringTableSize=FIXED, which means
  //   - it can degrade into linked list performance
  // - Hashed strings become GLOBAL_STR().  Never deallocated.
  // - Hashed strings become part of the "large object space", which might be
  //   managed by mark and sweep.  This requires linked list overhead.
  //   (doubly-linked?)
  // - Intern strings at GARBAGE COLLECTION TIME, with
  //   LayoutForwarded::new_location_?  Is this possible?  Does it introduce
  //   too much coupling between strings, hash tables, and GC?
  int hash_value_;
  char data_[1];  // flexible array

 private:
  int _strip_left_pos();
  int _strip_right_pos();

  DISALLOW_COPY_AND_ASSIGN(Str)
};

constexpr int kStrHeaderSize = offsetof(Str, data_);

inline void Str::SetObjLenFromStrLen(int str_len) {
  obj_len_ = kStrHeaderSize + str_len + 1;
}

inline int len(const Str* s) {
  // NOTE(Jesse): Not sure if 0-length strings should be allowed, but we
  // currently don't hit this assertion, so I would think not?
  assert(s->obj_len_ >= kStrHeaderSize - 1);

  return s->obj_len_ - kStrHeaderSize - 1;
}

// Notes:
// - sizeof("foo") == 4, for the NUL terminator.
// - gc_heap_test.cc has a static_assert that GlobalStr matches Str.  We don't
// put it here because it triggers -Winvalid-offsetof

//
// String "Constructors".  We need these because of the "flexible array"
// pattern.  I don't think "new Str()" can do that, and placement new would
// require mycpp to generate 2 statements everywhere.
//

inline Str* AllocStr(int len) {
  int obj_len = kStrHeaderSize + len + 1;
  void* place = gHeap.Allocate(obj_len);
  auto s = new (place) Str();
  s->SetObjLen(obj_len);
  return s;
}

// Like AllocStr, but allocate more than you need, e.g. for snprintf() to write
// into.  CALLER IS RESPONSIBLE for calling s->SetObjLenFromStrLen() afterward!
inline Str* OverAllocatedStr(int len) {
  int obj_len = kStrHeaderSize + len + 1;  // NUL terminator
  void* place = gHeap.Allocate(obj_len);
  auto s = new (place) Str();
  return s;
}

inline Str* StrFromC(const char* data, int len) {
  Str* s = AllocStr(len);
  memcpy(s->data_, data, len);
  assert(s->data_[len] == '\0');  // should be true because Heap was zeroed

  return s;
}

inline Str* StrFromC(const char* data) {
  return StrFromC(data, strlen(data));
}

// NOTE: This iterates over bytes.
class StrIter {
 public:
  explicit StrIter(Str* s) : s_(s), i_(0), len_(len(s)) {
    // We need this because StrIter is directly on the stack, and s_ could be
    // moved during iteration.
    gHeap.PushRoot(reinterpret_cast<Obj**>(&s_));
  }
  ~StrIter() {
    gHeap.PopRoot();
  }
  void Next() {
    i_++;
  }
  bool Done() {
    return i_ >= len_;
  }
  Str* Value() {  // similar to index_()
    // TODO: create 256 GLOBAL_STR() and return those instead!
    Str* result = AllocStr(1);
    result->data_[0] = s_->data_[i_];
    // assert(result->data_[1] == '\0');
    return result;
  }

 private:
  Str* s_;
  int i_;
  int len_;

  DISALLOW_COPY_AND_ASSIGN(StrIter)
};

bool maybe_str_equals(Str* left, Str* right);

// TODO(Jesse): Where should this go?  Certainly not here..
extern Str* kEmptyString;

template <int N>
class GlobalStr {
  // A template type with the same layout as Str with length N-1 (which needs a
  // buffer of size N).  For initializing global constant instances.
 public:
  OBJ_HEADER()

  int hash_value_;
  const char data_[N];

  DISALLOW_COPY_AND_ASSIGN(GlobalStr)
};

// This macro is a workaround for the fact that it's impossible to have a
// a constexpr initializer for char[N].  The "String Literals as Non-Type
// Template Parameters" feature of C++ 20 would have done it, but it's not
// there.
//
// https://old.reddit.com/r/cpp_questions/comments/j0khh6/how_to_constexpr_initialize_class_member_thats/
// https://stackoverflow.com/questions/10422487/how-can-i-initialize-char-arrays-in-a-constructor

#define GLOBAL_STR(name, val)                                            \
  GlobalStr<sizeof(val)> _##name = {                                     \
      Tag::Global, 0, kZeroMask, kStrHeaderSize + sizeof(val), -1, val}; \
  Str* name = reinterpret_cast<Str*>(&_##name);

#endif  // STR_TYPES_H
