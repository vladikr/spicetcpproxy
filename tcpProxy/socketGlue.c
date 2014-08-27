
#include <Python.h>
#include <dirent.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <sys/time.h>
#include <errno.h>
#include <sys/socket.h>
#include <sys/ioctl.h>
#include <netinet/in.h>
static PyObject *gluesockets(PyObject *self, PyObject *args);
static PyMethodDef GlueSocketsMethods[];
static PyObject *SelectError;

#define BUF_SIZE 4096    /* Buffer for  transfers */
#define SPLICE_LEN 4096
#undef SELECT_USES_HEAP
#if FD_SETSIZE > 1024
#define SELECT_USES_HEAP
#endif /* FD_SETSIZE > 1024 */

struct conn_socks
{
    int connected;
    int fd_src;
    int fd_dest;
};

static PyMethodDef
GlueSocketsMethods[] = {
    {"gluesockets",  gluesockets, METH_VARARGS,
     "Execute a command."},
    {NULL, NULL, 0, NULL}        /* Sentinel */
};

PyMODINIT_FUNC
initgluesockets(void)
{
    PyObject *m;

    m = Py_InitModule("gluesockets", GlueSocketsMethods);

    // In the future put other init code after this condition.
    if (m == NULL)
        return;
}

struct conn_socks sessions[7];
fd_set fdset, fderrset;
int fd_max;
int fd_listen, fd_dest;
//struct sockaddr_in dest_server_addr;
int conn_sessions = 0;
char *dest_server_addr;
int dest_server_port;

static PyObject *
gluesockets(PyObject *self, PyObject *args)
{
    int readsocks;       /* Number of sockets ready for reading */
    struct timeval timeout;
    timeout.tv_sec = 1;
    timeout.tv_usec = 0;
    int disconnected = 0;

    PyObject *pyfd_listen;
    PyObject *py_server_addr, *py_server_port;
    if (!PyArg_UnpackTuple(args, "gluesockets", 2, 3,
                              &pyfd_listen, &py_server_addr, &py_server_port))
            return NULL;

    fd_listen = PyObject_AsFileDescriptor(pyfd_listen);
    dest_server_addr = PyString_AsString(py_server_addr);
    dest_server_port = (int) PyInt_AsLong(py_server_port);

    for (readsocks = 0; readsocks < 8; readsocks++)
        sessions[readsocks].connected = 0;

    while (!disconnected) {
        prepare_select();

        //Py_BEGIN_ALLOW_THREADS
        readsocks = select(fd_max, &fdset, NULL, &fderrset, &timeout);
        //Py_END_ALLOW_THREADS

        if (readsocks < 0) {
            PyErr_SetFromErrno(SelectError);
            exit(-1);
        }
        else {
            if (readsocks > 0) {
         //       printf("Prepre FD_MAX: %d, ready: %d\n", fd_max, readsocks);
            //disconnected = check_closed_fds(&fderrset, fd_in, fd_out);
            disconnected = (!disconnected) ? handle_reads() : disconnected;
            if (disconnected > 0)
                printf("disconnect b4 while %d\n", disconnected);
            }
        }
    }
    return 0;
}

/*void get_dest_host_details(int fd_dest){

    int len = sizeof(struct sockaddr);

    getsockname(fd_dest, (struct sockaddr *) &dest_server_addr, &len);
    char *dest_host_addr = inet_ntoa(dest_server_addr.sin_addr);
    printf("Got host: %s", dest_host_addr);
    int dest_host_port = ntohs(dest_server_addr.sin_port);
    printf("port: %d", dest_host_port);
}*/

void prepare_select()
{
    int ind;
    FD_ZERO(&fdset);
    FD_SET(fd_listen, &fdset);
    FD_ZERO(&fderrset);
    FD_SET(fd_listen, &fderrset);

    fd_max = fd_listen;
    fd_max++;
    for (ind = 0; ind < 8; ind++) {
        if (sessions[ind].connected > 0) {
            FD_SET(sessions[ind].fd_src,&fdset);
            FD_SET(sessions[ind].fd_dest,&fdset);
            if (sessions[ind].fd_src > fd_max)
                fd_max = sessions[ind].fd_src;
            if (sessions[ind].fd_dest > fd_max)
                fd_max = sessions[ind].fd_dest;
            fd_max++;
        }
    }
}

void set_nonblocking(int fd)
{
    int opts;

    if (!(opts = fcntl(fd, F_GETFL))){
        perror("fcntl(F_GETFL)");
        exit(-1);
    }
    opts = (opts | O_NONBLOCK);
    if (fcntl(fd, F_SETFL, opts) < 0) {
        perror("fcntl(F_SETFL)");
        exit(-1);
    }
}


void conncet_to_dest()
{
    struct sockaddr_in dest_addr;
    int mysocket;
    mysocket = socket(AF_INET, SOCK_STREAM, 0);
    sessions[conn_sessions].fd_dest = mysocket;
    if ((sessions[conn_sessions].fd_dest = socket(AF_INET, SOCK_STREAM, 0)) < 0)
    {
      perror("socket()");
      exit(-1);
    }
    memset(&dest_addr, 0, sizeof(dest_addr));
    dest_addr.sin_family = AF_INET;
    dest_addr.sin_addr.s_addr =  inet_addr(dest_server_addr);
    dest_addr.sin_port = htons(dest_server_port);

    if (connect(mysocket,
        (struct sockaddr *) &dest_addr, sizeof(struct sockaddr)) < 0)
    {
      printf("Failed connect!\n");
      perror("connect()");
      exit(-1);
    }
    sessions[conn_sessions].fd_dest = 11;
    sessions[conn_sessions].fd_dest = mysocket;
}

void conn_new_session()
{

    if(!(sessions[conn_sessions].fd_src = accept(fd_listen, NULL, NULL))) {
        perror("accept");
        exit(-1);
    }

    conncet_to_dest();

    sessions[conn_sessions].connected = 1;
    conn_sessions++;

    set_nonblocking(sessions[conn_sessions-1].fd_src);
    set_nonblocking(sessions[conn_sessions-1].fd_dest);
}

int transfer(int from, int to)
{
    char buf[BUF_SIZE];
    int disconnected = 0;
    size_t bytes_read, bytes_written;
    if (FD_ISSET(from, &fdset))
    bytes_read = read(from, buf, BUF_SIZE);
    if (bytes_read == 0) {
        disconnected = 1;
    }
    else {
        bytes_written = write(to, buf, bytes_read);
        if (bytes_written == -1) {
            disconnected = 2;
        }
    }
    return disconnected;
}

ssize_t spliceit (int fd_in, int fd_out)
{
    int pipes[2];
    int numbytes = -1;
    int disconnected = 0;
    if (!pipe(pipes)){
        if (FD_ISSET(fd_in, &fdset)) {
            numbytes = splice(fd_in, NULL, pipes[1], NULL,
                              1024, SPLICE_F_MOVE|SPLICE_F_MORE);
            if (numbytes>0) {
                numbytes = splice(pipes[0], NULL, fd_out, NULL,
                             numbytes, SPLICE_F_MOVE|SPLICE_F_MORE);
            }
        if (numbytes<0) {
            perror ("splice");
            disconnected = 2;
        }
    } else {
        printf("Problem opening a pipe!\n");
    }
}
close(pipes[1]);
close(pipes[0]);

return disconnected;
}


int check_closed_fds(fd_set *ifdset, int fd_in, int fd_out)
{
    if (FD_ISSET(fd_in, ifdset)||FD_ISSET(fd_out, ifdset)) {
        return 1;
    }
    return 0;
}

int can_write_now(int fd)
{
  struct timeval timeout;
  fd_set s;

  FD_ZERO(&s);
  FD_SET(fd, &s);

  timeout.tv_sec = 0;
  timeout.tv_usec = 0;

  if (select(fd+1, NULL, &s, NULL, &timeout)==-1)
    return -1;

  return FD_ISSET(fd, &s)? 0: -1;
}

int read_once(int fd)
{
  struct timeval timeout;
  fd_set s1;

  FD_ZERO(&s1);
  FD_SET(fd, &s1);

  timeout.tv_sec = 0;
  timeout.tv_usec = 0;

  if (select(fd+1, &s1, NULL, NULL, &timeout)==-1)
    return -1;

  return FD_ISSET(fd, &s1)? 0: -1;
}

int handle_reads()
{
    int rfd_in, rfd_out;
    int set_flag=0;
    int disconnected=0;
    int ind;

    if (FD_ISSET(fd_listen, &fdset)) {
        conn_new_session();
    } else {
        for (ind = 0; ind < 8; ind++) {
            if (sessions[ind].connected == 1) {

                if (FD_ISSET(sessions[ind].fd_src, &fdset)) {
                    rfd_in = sessions[ind].fd_src;
                    rfd_out = sessions[ind].fd_dest;
                    set_flag = 1;
                }
                if (FD_ISSET(sessions[ind].fd_dest, &fdset)) {
                    rfd_in = sessions[ind].fd_dest;
                    rfd_out = sessions[ind].fd_src;
                    set_flag = 1;
                }

                if (set_flag>0){
                    disconnected = transfer(rfd_in, rfd_out);
                    //disconnected = spliceit(rfd_in, rfd_out);
                    if (disconnected > 0)
                        printf("disconnect in handle_reads %d\n", disconnected);
                }
                set_flag = 0;
            }
        }
    }
    return disconnected;
}




